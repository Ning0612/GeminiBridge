# Architecture Guide

Comprehensive architectural documentation for GeminiBridge v2.0.0

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Principles](#architecture-principles)
- [Component Architecture](#component-architecture)
- [Request Flow](#request-flow)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Concurrency Model](#concurrency-model)
- [Error Handling](#error-handling)
- [Logging Architecture](#logging-architecture)
- [Performance Considerations](#performance-considerations)
- [Scalability](#scalability)

## System Overview

GeminiBridge is a proxy server that provides OpenAI API compatibility for Google's Gemini models. It acts as a translation layer between OpenAI-formatted requests and Gemini CLI commands.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Python   │  │JavaScript│  │  cURL    │  │  Other   │   │
│  │ Client   │  │ Client   │  │ Client   │  │ Clients  │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘   │
└────────┼─────────────┼─────────────┼─────────────┼─────────┘
         │             │             │             │
         └─────────────┴─────────────┴─────────────┘
                           │
                OpenAI API Format (HTTP/JSON)
                           │
         ┌─────────────────▼─────────────────┐
         │                                   │
┌────────┴────────────────────────────────────┴─────────┐
│               GeminiBridge Server                     │
│  ┌─────────────────────────────────────────────────┐  │
│  │          FastAPI Application Layer              │  │
│  │  ┌────────────────┐  ┌────────────────┐        │  │
│  │  │ Health Check   │  │ List Models    │        │  │
│  │  │ Endpoint       │  │ Endpoint       │        │  │
│  │  └────────────────┘  └────────────────┘        │  │
│  │  ┌─────────────────────────────────────────┐   │  │
│  │  │  Chat Completions Endpoint              │   │  │
│  │  │  (Streaming & Non-Streaming)            │   │  │
│  │  └─────────────────────────────────────────┘   │  │
│  └──────────────────────┬──────────────────────────┘  │
│                         │                             │
│  ┌──────────────────────▼──────────────────────────┐  │
│  │          Middleware Chain                       │  │
│  │  ┌───────────────────────────────────────────┐  │  │
│  │  │  1. Request Logging Middleware            │  │  │
│  │  │     - Assign request_id                   │  │  │
│  │  │     - Extract client IP                   │  │  │
│  │  │     - Track timestamp                     │  │  │
│  │  └───────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────┐  │  │
│  │  │  2. Rate Limiting Middleware              │  │  │
│  │  │     - Check per-IP rate limits            │  │  │
│  │  │     - Sliding window algorithm            │  │  │
│  │  │     - Return 429 if exceeded              │  │  │
│  │  └───────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────┐  │  │
│  │  │  3. Authentication Middleware             │  │  │
│  │  │     - Validate Bearer token               │  │  │
│  │  │     - Timing-safe comparison              │  │  │
│  │  │     - Return 401 if invalid               │  │  │
│  │  └───────────────────────────────────────────┘  │  │
│  │  ┌───────────────────────────────────────────┐  │  │
│  │  │  4. CORS Middleware                       │  │  │
│  │  │     - Handle preflight requests           │  │  │
│  │  │     - Validate origins                    │  │  │
│  │  │     - Add CORS headers                    │  │  │
│  │  └───────────────────────────────────────────┘  │  │
│  └─────────────────────┬───────────────────────────┘  │
│                        │                              │
│  ┌─────────────────────▼───────────────────────────┐  │
│  │         Business Logic Layer                    │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │  Request Validator                       │   │  │
│  │  │  - Validate message structure            │   │  │
│  │  │  - Check request size limits             │   │  │
│  │  │  - Validate model names                  │   │  │
│  │  └──────────────────┬───────────────────────┘   │  │
│  │                     │                            │  │
│  │  ┌──────────────────▼───────────────────────┐   │  │
│  │  │  Model Mapper                            │   │  │
│  │  │  - Map OpenAI → Gemini models            │   │  │
│  │  │  - Load from config/models.json          │   │  │
│  │  │  - Apply fallback if needed              │   │  │
│  │  └──────────────────┬───────────────────────┘   │  │
│  │                     │                            │  │
│  │  ┌──────────────────▼───────────────────────┐   │  │
│  │  │  Prompt Builder                          │   │  │
│  │  │  - Convert OpenAI messages format        │   │  │
│  │  │  - Build Gemini CLI prompt               │   │  │
│  │  │  - Limit conversation history            │   │  │
│  │  └──────────────────┬───────────────────────┘   │  │
│  └────────────────────┬┴───────────────────────────┘  │
│                       │                               │
│  ┌────────────────────▼────────────────────────────┐  │
│  │         Queue Manager                           │  │
│  │  - Semaphore-based concurrency control          │  │
│  │  - Queue timeout management                     │  │
│  │  - Statistics tracking                          │  │
│  │  - Wait time measurement                        │  │
│  └────────────────────┬────────────────────────────┘  │
│                       │                               │
│  ┌────────────────────▼────────────────────────────┐  │
│  │         Gemini CLI Adapter                      │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │  Async Wrapper (anyio thread pool)        │ │  │
│  │  └────────────────┬───────────────────────────┘ │  │
│  │  ┌────────────────▼───────────────────────────┐ │  │
│  │  │  Retry Logic                               │ │  │
│  │  │  - Detect Docker conflicts (exit 125)     │ │  │
│  │  │  - Extract container name                 │ │  │
│  │  │  - Cleanup containers (docker rm -f)      │ │  │
│  │  │  - Retry with backoff (max 3 attempts)    │ │  │
│  │  └────────────────┬───────────────────────────┘ │  │
│  │  ┌────────────────▼───────────────────────────┐ │  │
│  │  │  Subprocess Execution                      │ │  │
│  │  │  - Platform-specific handling             │ │  │
│  │  │  - CREATE_NO_WINDOW (Windows)             │ │  │
│  │  │  - Temporary workdir isolation            │ │  │
│  │  │  - Timeout management                     │ │  │
│  │  └────────────────┬───────────────────────────┘ │  │
│  └───────────────────┼─────────────────────────────┘  │
│                      │                                │
│  ┌───────────────────▼────────────────────────────┐   │
│  │         Logging System                         │   │
│  │  - Structured JSON logging                     │   │
│  │  - Dual file handlers (general + error)        │   │
│  │  - Daily rotation                              │   │
│  │  - Sensitive data masking                      │   │
│  │  - Auto-cleanup (retention policy)             │   │
│  └────────────────────────────────────────────────┘   │
└────────────────────────┬───────────────────────────────┘
                         │
                  Gemini CLI Protocol
                         │
                ┌────────▼─────────┐
                │   Gemini CLI     │
                │   (Sandboxed)    │
                └────────┬─────────┘
                         │
                    Docker Sandbox
                         │
                ┌────────▼─────────┐
                │  Gemini Models   │
                │   (Google AI)    │
                └──────────────────┘
```

## Architecture Principles

### 1. Separation of Concerns

Each component has a single, well-defined responsibility:

- **Middleware** - Cross-cutting concerns (auth, logging, rate limiting)
- **Validators** - Input validation and sanitization
- **Queue Manager** - Concurrency control
- **CLI Adapter** - External process execution
- **Logger** - Centralized logging

### 2. Async-First Design

- Non-blocking I/O using FastAPI and asyncio
- Thread pool for blocking operations (subprocess)
- Semaphore-based concurrency control
- Async middleware chain

### 3. Defense in Depth

Multiple security layers:

- Authentication (Bearer token)
- Rate limiting (per-IP)
- Input validation (request size, message format)
- Sandboxed execution (Docker)
- Error sanitization (remove sensitive data)
- Logging masking (automatic PII removal)

### 4. Fail-Safe Defaults

- Sandbox always enabled
- Bearer token authentication required
- Conservative rate limits (default: 100 req/min)
- Request size limits
- Queue timeouts

### 5. Observable Systems

- Structured JSON logging
- Request ID tracking
- Performance metrics (queue statistics)
- Health check endpoint
- Error tracking

## Component Architecture

### 1. Configuration System (`src/config.py`)

**Purpose:** Centralized configuration management

**Pattern:** Singleton with lazy initialization

```python
# Singleton pattern
_config: AppConfig | None = None

def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()  # Loads from .env
    return _config
```

**Key Features:**

- Environment variable loading via pydantic-settings
- Automatic type validation and conversion
- Model mappings from JSON file
- Security validation (token strength)
- Sensible defaults

**Design Decisions:**

- **Why Singleton?** - Single source of truth, prevent re-parsing .env
- **Why pydantic-settings?** - Type safety, automatic validation
- **Why separate models.json?** - Easy to update mappings without code changes

### 2. Gemini CLI Adapter (`src/gemini_cli.py`)

**Purpose:** Execute Gemini CLI with reliability and safety

**Pattern:** Async wrapper around blocking subprocess

```python
async def execute_gemini_cli(prompt, model, request_id):
    # Run in thread pool to avoid blocking event loop
    result = await anyio.to_thread.run_sync(
        execute_gemini_cli_sync,
        prompt, model, request_id
    )
    return result
```

**Key Features:**

- **Async Execution** - Non-blocking via thread pool
- **Retry Logic** - Automatic retry on Docker conflicts
- **Platform Handling** - Windows vs Unix subprocess configuration
- **Isolation** - Temporary workdir per request
- **Cleanup** - Automatic cleanup on completion/failure

**Retry Mechanism:**

```python
for attempt in range(max_retries + 1):
    result = _execute_gemini_cli_internal(...)

    if docker_conflict_detected(result):
        container_name = extract_container_name(result.stderr)
        
        # Wait for container to stop naturally first
        container_stopped = _wait_for_container_to_stop(container_name, timeout=2)
        
        if container_stopped:
            cleanup_success = _cleanup_docker_container(container_name, force_stop=False)
        else:
            # Force cleanup if still running after timeout
            cleanup_success = _cleanup_docker_container(container_name, force_stop=True)
        
        # Smart random delay based on attempt number
        # Attempt 0: 100-300ms, Attempt 1: 200-500ms, Attempt 2+: 300-800ms
        if attempt == 0:
            random_delay = random.uniform(0.1, 0.3)
        elif attempt == 1:
            random_delay = random.uniform(0.2, 0.5)
        else:
            random_delay = random.uniform(0.3, 0.8)
        
        total_delay = cleanup_wait_ms + random_delay
        time.sleep(total_delay)
        continue  # Retry

    break  # Success or non-retryable error
```

**Design Decisions:**

- **Why thread pool?** - Subprocess is blocking, can't use async directly
- **Why retry?** - Docker container conflicts are transient, retry usually succeeds
- **Why smart delays?** - Variable delays reduce concurrent retry conflicts, increasing success rate
- **Why wait for container stop?** - Graceful cleanup is faster and safer than force-stopping
- **Why temp workdir?** - Isolation prevents file conflicts between concurrent requests

### 3. Queue Manager (`src/queue_manager.py`)

**Purpose:** Control concurrent CLI executions

**Pattern:** Semaphore-based resource management

```python
class CLIQueueManager:
    def __init__(self, max_concurrent: int, queue_timeout: int, min_request_gap_ms: int = 500):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue_timeout = queue_timeout
        self._min_request_gap_ms = min_request_gap_ms
        self._last_request_completion_time = 0.0

    async def execute(self, request_id, operation):
        # Pre-semaphore random delay (10-50ms) to spread out concurrent starts
        random_delay_ms = random.uniform(10, 50)
        await asyncio.sleep(random_delay_ms / 1000)
        
        # Wait for semaphore (with timeout)
        await asyncio.wait_for(
            self._semaphore.acquire(),
            timeout=self._queue_timeout
        )
        
        # Enforce minimum gap between requests
        async with self._stats_lock:
            if self._last_request_completion_time > 0:
                elapsed_ms = (time.time() - self._last_request_completion_time) * 1000
                if elapsed_ms < self._min_request_gap_ms:
                    wait_ms = self._min_request_gap_ms - elapsed_ms
                    await asyncio.sleep(wait_ms / 1000)

        try:
            result = await operation()
            return result
        finally:
            async with self._stats_lock:
                self._last_request_completion_time = time.time()
            self._semaphore.release()
```

**Key Features:**

- **Concurrency Control** - Limits simultaneous CLI processes
- **Pre-Semaphore Random Delay** - 10-50ms random delay spreads out concurrent request starts
- **Request Gap Enforcement** - Minimum configurable gap (default 500ms) between consecutive requests
- **Queue Timeout** - Prevents infinite waiting
- **Statistics Tracking** - Active, queued, total processed
- **Thread-Safe** - Uses asyncio.Lock for stats and timing

**Design Decisions:**

- **Why semaphore?** - Simple, efficient, built-in to asyncio
- **Why timeout?** - Prevent resource exhaustion from slow requests
- **Why pre-semaphore delay?** - Reduces Docker container name conflicts on concurrent starts
- **Why request gap?** - Further reduces conflicts, provides throughput control
- **Why statistics?** - Monitoring and capacity planning

### 4. Logging System (`src/logger.py`)

**Purpose:** Structured, secure logging

**Pattern:** Custom JSON formatter with dual handlers

```python
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "extra": mask_sensitive_data(record.extra)
        }
        return json.dumps(log_data)
```

**Key Features:**

- **Structured Logging** - JSON format for easy parsing
- **Dual Handlers** - General (INFO+) and Error (ERROR+) logs
- **Daily Rotation** - Automatic file rotation at midnight
- **Auto-Cleanup** - Removes logs older than retention period
- **Data Masking** - Automatic PII and sensitive data removal

**Masking Strategy:**

```python
# Tokens: Show first/last 4 chars
"abc123xyz789" → "abc1***xyz9"

# IPs: Mask last segment
"192.168.1.100" → "192.168.1.***"

# Content: Random 65% masking
"Hello world" → "He**o *or**"
```

**Design Decisions:**

- **Why JSON?** - Machine-readable, integrates with log aggregators
- **Why dual handlers?** - Easy to identify errors, separate retention policies
- **Why masking?** - Compliance (GDPR, privacy), security

### 5. Prompt Builder (`src/prompt_builder.py`)

**Purpose:** Convert OpenAI messages to Gemini CLI format

**Pattern:** Stateless converter

```python
def build_prompt(messages: List[dict]) -> str:
    # Limit history
    limited = messages[-MAX_MESSAGES:]

    # Format conversion
    parts = []
    for msg in limited:
        parts.append(f"[{msg['role'].capitalize()}]")
        parts.append(msg['content'])
        parts.append("")  # Separator

    return "\n".join(parts).strip()
```

**Output Format:**

```
[System]
You are a helpful assistant.

[User]
What is the capital of France?

[Assistant]
The capital of France is Paris.

[User]
What about Germany?
```

**Design Decisions:**

- **Why limit history?** - Prevent oversized prompts, improve performance
- **Why this format?** - Compatible with Gemini CLI expectations
- **Why stateless?** - Simple, testable, no side effects

## Request Flow

### Non-Streaming Request Flow

```
1. Client HTTP Request
   ↓
2. FastAPI Receives Request
   ↓
3. Middleware Chain Execution
   ├─ Request Logging → Assign request_id, extract IP
   ├─ Rate Limiting → Check limits, return 429 if exceeded
   ├─ Authentication → Validate token, return 401 if invalid
   └─ CORS → Add CORS headers
   ↓
4. Route Handler (POST /v1/chat/completions)
   ↓
5. Request Validation
   ├─ Validate message structure
   ├─ Check request size limits
   └─ Return 400 if invalid
   ↓
6. Model Mapping
   ├─ Load model mappings
   ├─ Map OpenAI → Gemini model
   └─ Apply fallback if needed
   ↓
7. Prompt Building
   ├─ Limit conversation history
   ├─ Format messages
   └─ Generate Gemini CLI prompt
   ↓
8. Queue Manager
   ├─ Acquire semaphore (wait if needed)
   ├─ Check queue timeout
   └─ Return 504 if timeout
   ↓
9. CLI Adapter Execution
   ├─ Run in thread pool (async wrapper)
   ├─ Execute subprocess with retry logic
   ├─ Handle Docker conflicts
   └─ Cleanup temp workdir
   ↓
10. Response Processing
    ├─ Check CLI exit code
    ├─ Parse stdout/stderr
    └─ Log result (with masking)
    ↓
11. OpenAI Response Format
    ├─ Build ChatCompletionResponse
    ├─ Set finish_reason = "stop"
    └─ Return JSON response
    ↓
12. Client Receives Response
```

### Streaming Request Flow

Same as non-streaming through step 9, then:

```
10. Streaming Response Generation
    ├─ Execute full CLI request (pseudo-streaming)
    ├─ Wait for complete response
    └─ Stream in chunks:
        ├─ Initial chunk (role)
        ├─ Content chunk (response text)
        ├─ Final chunk (finish_reason)
        └─ [DONE] marker
    ↓
11. Client Receives SSE Stream
```

## Data Flow

### Configuration Flow

```
.env file
  ↓
pydantic-settings
  ↓
AppConfig instance (singleton)
  ↓
get_config() → Used by all components
```

### Model Mapping Flow

```
config/models.json
  ↓
load_model_mappings()
  ↓
Model mappings dict (singleton)
  ↓
get_model_mappings() → Used by request handler
```

### Logging Flow

```
Application event
  ↓
logger.info/error/warning()
  ↓
JsonFormatter
  ├─ Structure as JSON
  ├─ Mask sensitive data
  └─ Add timestamp
  ↓
File Handlers
  ├─ General log (INFO+)
  └─ Error log (ERROR+)
  ↓
Log files in logs/
  ├─ gemini-bridge-YYYY-MM-DD.log
  └─ error-YYYY-MM-DD.log
```

## Security Architecture

### Authentication Layer

```python
@app.middleware("http")
async def auth_middleware(request, call_next):
    # Extract token
    auth_header = request.headers.get("authorization")
    provided_token = auth_header.split()[1]

    # Timing-safe comparison
    if not hmac.compare_digest(provided_token, expected_token):
        return 401

    return await call_next(request)
```

**Security Features:**

- Timing-safe comparison (prevents timing attacks)
- Token padding for length equality
- No token logging (only masked)

### Rate Limiting Layer

```python
class RateLimiter:
    def check_rate_limit(self, ip: str):
        # Sliding window algorithm
        current_time = time.time()

        # Remove expired requests
        self.requests[ip] = [
            ts for ts in self.requests[ip]
            if current_time - ts < window_seconds
        ]

        # Check limit
        if len(self.requests[ip]) >= max_requests:
            return False, 0

        # Add current request
        self.requests[ip].append(current_time)
        return True, remaining
```

**Security Features:**

- Per-IP tracking
- Sliding window (more accurate than fixed window)
- Automatic cleanup of old requests
- Configurable limits

### Input Validation Layer

```python
# Message structure validation
valid_roles = {"system", "user", "assistant"}
for msg in messages:
    if msg["role"] not in valid_roles:
        return 400

# Request size validation
if len(messages) > 100:
    return 400
if len(msg["content"]) > 100000:
    return 400
```

**Security Features:**

- Prevents DoS via oversized requests
- Validates message structure
- Sanitizes error messages (removes paths, IPs)

## Concurrency Model

### Async Architecture

```python
# FastAPI async handler
async def chat_completions(request, body):
    # Async validation
    await validate_request(body)

    # Async queue execution
    result = await cli_queue.execute(
        request_id,
        lambda: execute_gemini_cli(...)  # Runs in thread pool
    )

    return result
```

### Thread Pool for Blocking Operations

```python
# Subprocess is blocking, so run in thread pool
async def execute_gemini_cli(prompt, model, request_id):
    result = await anyio.to_thread.run_sync(
        execute_gemini_cli_sync,  # Blocking subprocess.run()
        prompt, model, request_id
    )
    return result
```

### Semaphore-Based Concurrency Control

```
Request 1 ──┐
Request 2 ──┼─→ Semaphore (max_concurrent=5) ─→ CLI Process 1
Request 3 ──┤                                  ─→ CLI Process 2
Request 4 ──┤                                  ─→ CLI Process 3
Request 5 ──┤                                  ─→ CLI Process 4
Request 6 ──┘   (waits in queue)               ─→ CLI Process 5
Request 7 ──┐   (waits in queue)
Request 8 ──┘   (waits in queue)
```

## Error Handling

### Error Propagation

```
CLI Execution Error
  ↓
CLIExecutionResult(success=False, error=...)
  ↓
Check error type
  ├─ Docker conflict? → Retry
  ├─ Timeout? → Return 504
  └─ Other? → Return 500
  ↓
Sanitize error message
  ├─ Remove paths
  ├─ Remove IPs
  └─ Remove container IDs
  ↓
Log error (with masking)
  ↓
Return OpenAI error format
```

### Retry Logic

```python
for attempt in range(max_retries + 1):
    result = execute_cli_internal(...)

    if is_docker_conflict_error(result):
        if attempt >= max_retries:
            break  # Give up

        cleanup_docker_container()
        time.sleep(0.5)
        continue  # Retry

    break  # Success or non-retryable error
```

## Logging Architecture

### Log Structure

```json
{
    "timestamp": "2024-01-09T12:00:00.123456",
    "level": "INFO",
    "logger": "gemini_bridge",
    "message": "Request completed successfully",
    "extra": {
        "request_id": "abc-123",
        "execution_time_ms": 1234,
        "model": "gemini-2.5-pro",
        "prompt_preview": "He**o ***ld",
        "response_preview": "***"
    }
}
```

### Log Rotation

```
Day 1: gemini-bridge-2024-01-01.log (new)
Day 2: gemini-bridge-2024-01-02.log (new)
...
Day 8: gemini-bridge-2024-01-08.log (new)
       gemini-bridge-2024-01-01.log (deleted, 7-day retention)
```

## Performance Considerations

### Bottlenecks

1. **CLI Execution** - Subprocess creation and Docker overhead
2. **Queue Waiting** - When concurrent limit reached
3. **I/O Operations** - File logging, config loading

### Optimizations

1. **Thread Pool** - Prevents blocking event loop
2. **Concurrency Control** - Prevents resource exhaustion
3. **Configuration Caching** - Singleton pattern, load once
4. **Prompt Limiting** - Max 20 messages per request
5. **Async I/O** - Non-blocking request handling

### Performance Metrics

- **Queue Statistics** - Available via `/health` endpoint
- **Average Wait Time** - Tracked by queue manager
- **Active Requests** - Real-time monitoring
- **Total Processed** - Cumulative counter

## Scalability

### Vertical Scaling

Increase `MAX_CONCURRENT_REQUESTS`:
```bash
MAX_CONCURRENT_REQUESTS=10  # Default: 5
```

**Limitations:**
- CPU cores (subprocess overhead)
- Memory (Docker containers)
- Docker capacity

### Horizontal Scaling

Deploy multiple instances behind load balancer:

```
                 Load Balancer
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   Instance 1    Instance 2    Instance 3
   (port 11434)  (port 11435)  (port 11436)
```

**Considerations:**

- Stateless design (no shared state)
- Independent rate limiters (per-instance, per-IP)
- Shared log aggregation (e.g., ELK stack)
- Health check monitoring

### Cloud Deployment

**Recommended Architecture:**

```
Internet
  │
  ├─ Cloud Load Balancer (HTTPS)
  │
  ├─ Auto-Scaling Group
  │   ├─ Container Instance 1
  │   ├─ Container Instance 2
  │   └─ Container Instance 3
  │
  ├─ Shared Log Storage (S3, CloudWatch)
  └─ Monitoring (Prometheus, Grafana)
```

## Design Patterns Used

1. **Singleton** - Configuration, model mappings, queue manager
2. **Middleware Chain** - Request processing pipeline
3. **Adapter** - Gemini CLI adapter (interface adaptation)
4. **Factory** - Logger setup, JSON formatter
5. **Strategy** - Model mapping (configurable strategy)
6. **Observer** - Logging (event-driven)
7. **Retry** - CLI execution with exponential backoff

## Future Improvements

### Potential Enhancements

1. **Caching Layer** - Cache identical prompts/responses
2. **Database Integration** - Persistent request history
3. **WebSocket Support** - True streaming (not pseudo)
4. **Multiple CLI Backends** - Support different Gemini CLI versions
5. **Metrics Export** - Prometheus metrics endpoint
6. **Distributed Rate Limiting** - Redis-based rate limiter
7. **Request Prioritization** - Priority queue for important requests
8. **Circuit Breaker** - Prevent cascading failures

### Migration Path

Current architecture supports these enhancements without major refactoring:

- Configuration system → Add new settings
- Queue manager → Replace semaphore with priority queue
- CLI adapter → Add backend selection logic
- Logging → Add metrics exporter

---

For implementation details, see:
- [API Documentation](API.md)
- [Development Guide](DEVELOPMENT.md)
- [Security Guide](SECURITY.md)
