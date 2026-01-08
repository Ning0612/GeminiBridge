"""
GeminiBridge Python - FastAPI Application
OpenAI API-compatible proxy for Gemini CLI
"""

import hmac
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Any

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import get_config, get_model_mappings, get_default_model
from .prompt_builder import build_prompt, validate_messages, validate_request_size
from .gemini_cli import execute_gemini_cli
from .queue_manager import get_cli_queue
from .logger import get_logger, mask_content


# ============================================================================
# Logger
# ============================================================================

# Use 'gemini_bridge' to ensure we use the same logger configured in main.py
logger = get_logger("gemini_bridge")


# ============================================================================
# Models (Pydantic)
# ============================================================================

class Message(BaseModel):
    """OpenAI message format"""
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI chat completion request"""
    model: str
    messages: List[Message]
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None


class ChatCompletionChoice(BaseModel):
    """Chat completion choice"""
    index: int
    message: Dict[str, str]
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    """OpenAI chat completion response"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]


class ChatCompletionChunk(BaseModel):
    """OpenAI streaming chunk"""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


class ErrorResponse(BaseModel):
    """OpenAI error response"""
    error: Dict[str, Any]


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    object: str = "model"


class ModelsListResponse(BaseModel):
    """Models list response"""
    object: str = "list"
    data: List[ModelInfo]


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter with sliding window"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}  # IP -> [timestamps]

    def _cleanup_old_requests(self, ip: str, current_time: float) -> None:
        """Remove requests outside the time window"""
        if ip in self.requests:
            self.requests[ip] = [
                ts for ts in self.requests[ip]
                if current_time - ts < self.window_seconds
            ]

    def check_rate_limit(self, ip: str) -> tuple[bool, int]:
        """
        Check if request is allowed

        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        current_time = time.time()

        # Cleanup old requests
        self._cleanup_old_requests(ip, current_time)

        # Initialize if new IP
        if ip not in self.requests:
            self.requests[ip] = []

        # Check limit
        request_count = len(self.requests[ip])
        if request_count >= self.max_requests:
            return False, 0

        # Add current request
        self.requests[ip].append(current_time)

        remaining = self.max_requests - request_count - 1
        return True, remaining


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    config = get_config()
    logger.info(
        "GeminiBridge Python starting",
        extra={"extra": {
            "host": config.host,
            "port": config.port,
            "max_concurrent_requests": config.max_concurrent_requests,
            "cli_timeout": config.gemini_cli_timeout,
            "rate_limit_max_requests": config.rate_limit_max_requests,
            "rate_limit_window_seconds": config.rate_limit_window_seconds
        }}
    )

    yield

    logger.info("GeminiBridge Python shutting down")


# ============================================================================
# FastAPI Application
# ============================================================================

config = get_config()

app = FastAPI(
    title="GeminiBridge Python",
    description="OpenAI API-compatible proxy for Gemini CLI",
    version="2.0.0",
    lifespan=lifespan
)

# Global instances
rate_limiter = RateLimiter(
    max_requests=config.rate_limit_max_requests,
    window_seconds=config.rate_limit_window_seconds
)
cli_queue = get_cli_queue()


# ============================================================================
# Middleware
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*",
        "chrome-extension://*",
        "moz-extension://*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Request logging and context middleware"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.timestamp = time.time()

    # Get client IP (support X-Forwarded-For)
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0] if forwarded else request.client.host

    request.state.client_ip = client_ip

    response = await call_next(request)
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = getattr(request.state, "client_ip", request.client.host)

    allowed, remaining = rate_limiter.check_rate_limit(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "message": "Rate limit exceeded. Please try again later.",
                    "type": "rate_limit_exceeded",
                    "code": "rate_limit_exceeded"
                }
            }
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Bearer token authentication middleware"""
    # Skip auth for health check
    if request.url.path == "/health":
        return await call_next(request)

    auth_header = request.headers.get("authorization")

    if not auth_header:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "message": "Missing authorization header",
                    "type": "authentication_error",
                    "code": "missing_auth_header"
                }
            }
        )

    # Check Bearer token format
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "message": "Invalid authorization header format",
                    "type": "authentication_error",
                    "code": "invalid_auth_header"
                }
            }
        )

    provided_token = parts[1]
    expected_token = config.bearer_token

    # Timing-safe comparison (prevent timing attacks)
    # Note: hmac.compare_digest requires same-length strings
    # Pad to same length if needed
    max_len = max(len(provided_token), len(expected_token))
    provided_padded = provided_token.ljust(max_len)
    expected_padded = expected_token.ljust(max_len)

    if not hmac.compare_digest(provided_padded, expected_padded):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "message": "Invalid bearer token",
                    "type": "authentication_error",
                    "code": "invalid_token"
                }
            }
        )

    response = await call_next(request)
    return response


# ============================================================================
# Routes
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint with queue statistics"""
    stats = await cli_queue.get_stats()

    return {
        "status": "healthy",
        "service": "GeminiBridge Python",
        "version": "2.0.0",
        "queue": {
            "active_requests": stats.active_requests,
            "queued_requests": stats.queued_requests,
            "total_processed": stats.total_processed,
            "average_wait_time_ms": stats.average_wait_time_ms,
            "max_concurrent": stats.max_concurrent
        }
    }


@app.get("/v1/models")
async def list_models():
    """List available models"""
    model_mappings = get_model_mappings()

    models = [
        ModelInfo(id=model_id)
        for model_id in model_mappings.keys()
    ]

    return ModelsListResponse(data=models)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    """
    Chat completions endpoint (streaming and non-streaming)
    Matches OpenAI API format
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    start_time = time.time()

    # Validate messages
    messages_dict = [msg.model_dump() for msg in body.messages]

    valid, error_msg = validate_messages(messages_dict)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": error_msg,
                    "type": "invalid_request_error",
                    "param": "messages"
                }
            }
        )

    # Validate request size
    valid, error_msg = validate_request_size(messages_dict)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": error_msg,
                    "type": "invalid_request_error",
                    "param": "messages"
                }
            }
        )

    # Map model (with fallback)
    model_mappings = get_model_mappings()
    requested_model = body.model

    # Check if it's already a Gemini model (starts with 'gemini-')
    if requested_model.startswith("gemini-"):
        # Direct Gemini model request, no mapping needed
        mapped_model = requested_model
        logger.info(
            "Direct Gemini model request",
            extra={"extra": {"requested_model": requested_model, "request_id": request_id}}
        )
    elif requested_model in model_mappings:
        # Found in mappings
        mapped_model = model_mappings[requested_model]
        logger.info(
            "Model mapping applied",
            extra={"extra": {"requested_model": requested_model, "mapped_model": mapped_model, "request_id": request_id}}
        )
    else:
        # Not found, use fallback
        mapped_model = get_default_model()
        logger.warning(
            "Model not in mappings, using fallback",
            extra={"extra": {"requested_model": requested_model, "fallback_model": mapped_model, "request_id": request_id}}
        )

    # Build prompt
    prompt = build_prompt(messages_dict)

    # Check if streaming requested
    if body.stream:
        return await handle_streaming_request(
            request_id, requested_model, mapped_model, prompt, start_time
        )
    else:
        return await handle_non_streaming_request(
            request_id, requested_model, mapped_model, prompt, start_time
        )


async def handle_non_streaming_request(
    request_id: str,
    requested_model: str,
    mapped_model: str,
    prompt: str,
    start_time: float
) -> ChatCompletionResponse:
    """Handle non-streaming chat completion request"""

    # Execute CLI with queue management
    result = await cli_queue.execute(
        request_id,
        lambda: execute_gemini_cli(prompt, mapped_model, request_id)
    )

    execution_time_ms = int((time.time() - start_time) * 1000)

    if not result.success:
        # Log error with details
        error_msg = result.error or "Unknown error"
        logger.error(
            "Request failed",
            extra={"extra": {
                "request_id": request_id,
                "execution_time_ms": execution_time_ms,
                "error": error_msg,
                "stderr": result.stderr,
                "model": mapped_model,
                "prompt_preview": mask_content(prompt, max_length=100)
            }}
        )

        # Map error to appropriate HTTP status
        if "timeout" in error_msg.lower():
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": {
                    "message": error_msg,
                    "type": "api_error",
                    "code": "model_error"
                }
            }
        )

    # Log success
    logger.info(
        "Request completed successfully",
        extra={"extra": {
            "request_id": request_id,
            "execution_time_ms": execution_time_ms,
            "model": mapped_model,
            "prompt_preview": mask_content(prompt, max_length=100),
            "response_preview": mask_content(result.content or "", max_length=100),
            "response_length": len(result.content or "")
        }}
    )

    # Build OpenAI response
    response = ChatCompletionResponse(
        id=f"chatcmpl-{request_id}",
        created=int(time.time()),
        model=requested_model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message={"role": "assistant", "content": result.content or ""},
                finish_reason="stop"
            )
        ]
    )

    return response


async def handle_streaming_request(
    request_id: str,
    requested_model: str,
    mapped_model: str,
    prompt: str,
    start_time: float
) -> StreamingResponse:
    """
    Handle streaming chat completion request
    Note: This is pseudo-streaming (execute full, then stream chunks)
    """

    async def generate_sse_stream():
        """Generate SSE stream chunks"""
        try:
            # Execute CLI with queue management
            result = await cli_queue.execute(
                request_id,
                lambda: execute_gemini_cli(prompt, mapped_model, request_id)
            )

            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Streaming request completed successfully",
                extra={"extra": {
                    "request_id": request_id,
                    "execution_time_ms": execution_time_ms,
                    "model": mapped_model,
                    "prompt_preview": mask_content(prompt, max_length=100),
                    "response_preview": mask_content(result.content or "", max_length=100),
                    "response_length": len(result.content or "")
                }}
            )

            if not result.success:
                # Send error chunk
                error_chunk = {
                    "error": {
                        "message": result.error or "Unknown error",
                        "type": "api_error",
                        "code": "model_error"
                    }
                }
                yield f"data: {error_chunk}\n\n"
                return

            # Send chunks in OpenAI format
            created_ts = int(time.time())

            # 1. Initial chunk with role
            initial_chunk = ChatCompletionChunk(
                id=f"chatcmpl-{request_id}",
                created=created_ts,
                model=requested_model,
                choices=[
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None
                    }
                ]
            )
            yield f"data: {initial_chunk.model_dump_json()}\n\n"

            # 2. Content chunk (complete response)
            if result.content:
                content_chunk = ChatCompletionChunk(
                    id=f"chatcmpl-{request_id}",
                    created=created_ts,
                    model=requested_model,
                    choices=[
                        {
                            "index": 0,
                            "delta": {"content": result.content},
                            "finish_reason": None
                        }
                    ]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"

            # 3. Final chunk with finish_reason
            final_chunk = ChatCompletionChunk(
                id=f"chatcmpl-{request_id}",
                created=created_ts,
                model=requested_model,
                choices=[
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"

            # 4. [DONE] marker
            yield "data: [DONE]\n\n"

        except Exception as e:
            # Send error chunk
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "api_error",
                    "code": "internal_error"
                }
            }
            yield f"data: {error_chunk}\n\n"

    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=False
    )
