# GeminiBridge Technical Architecture

Detailed technical architecture and implementation documentation for GeminiBridge.

## System Overview

GeminiBridge is an OpenAI API-compatible proxy server that translates OpenAI API requests into Google Gemini CLI executions. The system acts as a bridge between applications expecting OpenAI's API format and local Gemini models executed via CLI.

### Design Goals

1. **API Compatibility**: 100% OpenAI API compatibility for seamless integration
2. **Security First**: Sandboxed CLI execution, authentication, and rate limiting
3. **UTF-8 Support**: Full international character support (Windows optimized)
4. **Graceful Degradation**: Fallback mechanisms for unmapped models
5. **Production Ready**: Comprehensive error handling, logging, and monitoring

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│  (Browser Extensions, Chat Tools, Custom Applications)      │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/HTTPS
                     │ OpenAI API Format
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   GeminiBridge Server                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Middleware Stack (Ordered)                │   │
│  │  1. CORS           → Browser extension support       │   │
│  │  2. Body Parser    → JSON + UTF-8 handling           │   │
│  │  3. Request Logger → UUID, IP, User-Agent tracking   │   │
│  │  4. Rate Limiter   → Sliding window, per-IP          │   │
│  │  5. Auth           → Bearer token validation         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    Route Handlers                     │   │
│  │  • GET  /health                                       │   │
│  │  • GET  /v1/models                                    │   │
│  │  • POST /v1/chat/completions                          │   │
│  │  • POST /chat/completions (alias)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Business Logic                       │   │
│  │  • Message Validation                                 │   │
│  │  • Model Mapping (with fallback)                      │   │
│  │  • Prompt Building (OpenAI → Gemini format)           │   │
│  │  • Response Formatting (Gemini → OpenAI format)       │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Gemini CLI Adapter                       │   │
│  │  • Process Spawning (child_process)                   │   │
│  │  • Stdin UTF-8 Encoding                               │   │
│  │  • Stdout Plain Text Capture                          │   │
│  │  • Temp Directory Management                          │   │
│  │  • Timeout Enforcement                                │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │ Child Process
                     │ CLI Execution
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Gemini CLI Process                        │
│  • Sandboxed Execution (--sandbox flag)                     │
│  • Model-specific Inference                                 │
│  • Plain Text Output                                        │
│  • Temporary Working Directory                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Server Layer (`src/server.ts`)

**Responsibilities:**
- Express application setup and configuration
- Middleware stack orchestration
- Route mounting
- Graceful shutdown handling
- UTF-8 encoding setup (Windows)

**Key Features:**
- UTF-8 console encoding on Windows (`chcp 65001`)
- Global error handler
- Graceful shutdown on SIGTERM/SIGINT
- Uncaught exception/rejection handlers

**Startup Sequence:**
```typescript
1. Load environment configuration
2. Set UTF-8 encoding (Windows)
3. Create Express app
4. Apply middleware (order critical!)
5. Mount routes
6. Start HTTP server
7. Register signal handlers
```

### 2. Middleware Stack

#### Order of Execution (Critical!)

1. **CORS** (`src/middleware/cors.ts`)
   - Allows browser extensions and localhost
   - Origins: `localhost`, `127.0.0.1`, `chrome-extension://`, `moz-extension://`
   - Methods: `GET`, `POST`, `OPTIONS`

2. **Body Parser** (Express built-in)
   - JSON parsing with 10MB limit
   - UTF-8 charset support
   - Request body debugging (POST `/chat/completions` only)

3. **Request Logger** (`src/middleware/request_logger.ts`)
   - Generates unique UUID per request
   - Captures: IP, User-Agent, timestamp
   - Attaches `RequestContext` to `req.context`

4. **Rate Limiter** (`src/middleware/rate_limit.ts`)
   - Sliding window algorithm
   - Default: 100 requests per 60 seconds
   - Tracked per IP address
   - Auto-cleanup every 60 seconds

5. **Authentication** (`src/middleware/auth.ts`)
   - Bearer token validation
   - Header format: `Authorization: Bearer <token>`
   - Returns 401 on invalid/missing token

### 3. Route Handlers

#### GET /v1/models (`src/routes/models.ts`)

**Flow:**
```typescript
1. Read model mappings from config
2. Map to OpenAI model format
3. Return as ModelsListResponse
```

**Response Structure:**
```json
{
  "object": "list",
  "data": [
    {"id": "gpt-3.5-turbo", "object": "model"},
    ...
  ]
}
```

#### POST /v1/chat/completions (`src/routes/chat.ts`)

**Non-Streaming Flow:**
```typescript
1. Validate request body (model, messages)
2. Validate message structure
3. Map model (fallback to gemini-2.5-flash)
4. Build prompt (OpenAI → Gemini format)
5. Execute Gemini CLI
6. Format response (Gemini → OpenAI format)
7. Return ChatCompletionResponse
```

**Pseudo-Streaming Flow:**
```typescript
1. Validate request body (model, messages)
2. Validate message structure
3. Map model (fallback to gemini-2.5-flash)
4. Build prompt (OpenAI → Gemini format)
5. Execute Gemini CLI (complete response)
6. Set SSE headers
7. Send initial chunk (role: assistant)
8. Send content chunk (full response)
9. Send final chunk (finish_reason: stop)
10. Send [DONE] marker
```

**Key Implementation Details:**
- Uses same `executeGeminiCLI()` for both modes
- Streaming is "pseudo-streaming" (not real-time)
- SSE format: `data: {json}\n\n`
- Error handling returns SSE error chunks

### 4. Gemini CLI Adapter (`src/adapters/gemini_cli.ts`)

#### executeGeminiCLI() Function

**Execution Pattern:**
```typescript
spawn(cliPath, ['-m', model, '--sandbox'], {
  cwd: tempWorkDir,
  stdio: ['pipe', 'pipe', 'pipe'],
  shell: true
});

// Write prompt to stdin as UTF-8 buffer
process.stdin.write(Buffer.from(prompt, 'utf8'));
process.stdin.end();

// Capture stdout as plain text
process.stdout.on('data', (data) => {
  stdout += data.toString();
});

// Wait for 'close' event (not 'exit')
process.on('close', (code) => {
  // Process complete stdout
  const content = stdout.trim();
  resolve({ success: true, content });
});
```

**Key Features:**
- **Sandbox mode**: Always uses `--sandbox` flag
- **Stdin for prompts**: Avoids shell encoding issues
- **UTF-8 handling**: Explicit buffer encoding
- **Temp directories**: Created per request, auto-cleanup
- **Timeout enforcement**: Hard timeout with process kill
- **'close' event**: Ensures stdout is fully flushed

#### GeminiStream Class (DEPRECATED)

**Status:** No longer used in production code

**Original Purpose:** Real-time streaming from CLI

**Why Deprecated:**
- Gemini CLI doesn't support true streaming output yet
- Current implementation uses pseudo-streaming instead
- Would need `--output-format stream-json` support

**Future Use:** Could be revived if CLI adds streaming support

### 5. Utility Modules

#### Prompt Builder (`src/utils/prompt_builder.ts`)

**Conversion Logic:**
```
OpenAI Format:
[
  {"role": "system", "content": "You are helpful"},
  {"role": "user", "content": "Hello"},
  {"role": "assistant", "content": "Hi there"}
]

Gemini CLI Format:
[System]
You are helpful

[User]
Hello

[Assistant]
Hi there
```

**Features:**
- Limits to last 20 messages (prevent oversized prompts)
- Validates role and content fields
- Empty line separators between messages

#### Error Handler (`src/utils/error_handler.ts`)

**Error Mapping:**

| Internal Code | HTTP Status | OpenAI Error Type |
|---------------|-------------|-------------------|
| `INVALID_REQUEST` | 400 | `invalid_request_error` |
| `AUTHENTICATION_ERROR` | 401 | `authentication_error` |
| `RATE_LIMIT_ERROR` | 429 | `rate_limit_exceeded` |
| `MODEL_ERROR` | 500 | `api_error` |
| `INVALID_RESPONSE_FORMAT` | 500 | `api_error` |
| `TIMEOUT` | 504 | `api_error` |
| `INTERNAL_ERROR` | 500 | `api_error` |

**Response Format:**
```json
{
  "error": {
    "message": "Error description",
    "type": "api_error",
    "code": "model_error",
    "param": "model"
  }
}
```

#### Logger (`src/utils/logger.ts`)

**Winston Configuration:**
- **Transports:**
  - Console (colorized, development)
  - File (`logs/gemini-bridge.log`, JSON, 10MB rotation)
  - Error file (`logs/error.log`, errors only)

**Log Levels:** `error`, `warn`, `info`, `debug`

**Request Logging Fields:**
```typescript
{
  requestId: string,      // UUID
  clientIp: string,       // Client IP
  userAgent: string,      // User-Agent header
  timestamp: Date,        // Request timestamp
  model: string,          // Requested model
  mappedModel: string,    // Actual Gemini model
  stream: boolean,        // Streaming mode
  exitCode: number,       // CLI exit code
  stderr: string,         // CLI error output
  latency: number,        // Request duration (ms)
  error?: string          // Error message (if failed)
}
```

### 6. Configuration (`src/config/index.ts`)

**Configuration Sources:**
1. Environment variables (`.env`)
2. Model mappings file (`config/models.json`)
3. Default fallback values

**Validation:**
- Checks required variables (`BEARER_TOKEN`)
- Validates numeric values (port, timeout, rate limits)
- Loads model mappings with fallback to defaults

**Singleton Pattern:**
```typescript
export const config = getConfig(); // Loaded once at startup
```

---

## Data Flow

### Non-Streaming Request

```
1. Client → POST /v1/chat/completions
   Body: {"model": "gpt-3.5-turbo", "messages": [...]}

2. Middleware Stack
   CORS → Parse → Log → Rate Limit → Auth

3. Route Handler (chat.ts)
   - Validate request
   - Map model: "gpt-3.5-turbo" → "gemini-2.5-flash"
   - Build prompt: messages → Gemini format

4. CLI Adapter (gemini_cli.ts)
   - Create temp dir
   - Spawn: gemini -m gemini-2.5-flash --sandbox
   - Write prompt to stdin
   - Wait for stdout (30s timeout)
   - Return plain text content

5. Response Formatter (chat.ts)
   - Build ChatCompletionResponse
   - choices[0].message.content = stdout

6. Client ← 200 OK
   {"id": "chatcmpl-xxx", "choices": [...], ...}
```

### Streaming Request (Pseudo-Streaming)

```
1. Client → POST /v1/chat/completions
   Body: {"model": "gpt-3.5-turbo", "messages": [...], "stream": true}

2. Middleware Stack (same as above)

3. Route Handler (chat.ts)
   - Validate request
   - Map model
   - Build prompt
   - Set SSE headers

4. CLI Adapter (gemini_cli.ts)
   - Execute CLI (same as non-streaming)
   - Return complete response

5. SSE Chunker (chat.ts)
   - Chunk 1: {"delta": {"role": "assistant"}, ...}
   - Chunk 2: {"delta": {"content": "full response"}, ...}
   - Chunk 3: {"delta": {}, "finish_reason": "stop"}
   - [DONE]

6. Client ← 200 OK (SSE stream)
   data: {...}
   data: {...}
   data: [DONE]
```

---

## Security Architecture

### Defense Layers

1. **Network Layer**
   - Localhost binding (127.0.0.1)
   - CORS restrictions
   - Rate limiting (100 req/min per IP)

2. **Authentication Layer**
   - Bearer token validation
   - No public endpoints (except /health)

3. **Execution Layer**
   - Sandboxed CLI execution (`--sandbox` flag)
   - Temporary isolated directories
   - Timeout enforcement (30s default)
   - Process cleanup on error/timeout

4. **Input Validation**
   - Message structure validation
   - Content type validation
   - Request size limits (10MB)

### Threat Mitigation

| Threat | Mitigation |
|--------|------------|
| **Command Injection** | Stdin for prompts (not CLI args) |
| **Path Traversal** | Isolated temp directories per request |
| **DoS (Rate)** | Sliding window rate limiter |
| **DoS (Resource)** | Timeout enforcement, process kill |
| **Unauthorized Access** | Bearer token authentication |
| **CORS Attacks** | Explicit origin whitelist |

---

## Performance Considerations

### Bottlenecks

1. **CLI Execution**: Synchronous per request (blocking)
2. **Temp Directory I/O**: Create/delete overhead
3. **No Request Queuing**: Concurrent CLI spawns

### Optimization Strategies

**Current:**
- In-memory rate limiting (no database)
- Lightweight middleware stack
- Minimal logging overhead

**Future:**
- Request queuing with concurrency limits
- Connection pooling for CLI processes
- Streaming output parsing (true real-time)
- Caching for repeated requests

### Scalability Limits

**Single Instance:**
- ~100 requests/min (rate limit)
- ~10-30 concurrent CLI processes (system dependent)
- Memory: ~50MB base + ~5MB per concurrent request

**Horizontal Scaling:**
- Stateless design (except rate limiter)
- Shared bearer token (needs centralized auth)
- Rate limiting needs shared state (Redis)

---

## Error Handling Strategy

### Error Propagation

```
CLI Error → Adapter → Route Handler → Error Handler → Client

Example:
1. CLI exits with code 1
2. Adapter: CLIExecutionResult { success: false, error: "..." }
3. Handler: handleCLIError(code, stderr)
4. Error Handler: sendError(res, errorDetails)
5. Client: 500 + OpenAI error format
```

### Graceful Degradation

1. **Model Mapping Failure**
   - Fallback to `gemini-2.5-flash`
   - Log warning, continue execution

2. **Temp Directory Cleanup Failure**
   - Log warning, don't fail request
   - Relies on OS temp cleanup

3. **Log File Write Failure**
   - Console fallback
   - Application continues

---

## Monitoring & Observability

### Logging Strategy

**Request Lifecycle:**
1. `logRequestStart()`: Request received
2. `logRequest()`: Request completed (success/failure)
3. `logError()`: Unexpected errors

**CLI Execution:**
- Stdout length and preview
- Stderr capture
- Exit code tracking
- Execution time

### Metrics (Future)

**Proposed Prometheus Metrics:**
- `gemini_bridge_requests_total` (counter)
- `gemini_bridge_request_duration_seconds` (histogram)
- `gemini_bridge_cli_execution_duration_seconds` (histogram)
- `gemini_bridge_active_requests` (gauge)
- `gemini_bridge_rate_limit_rejections_total` (counter)

---

## Configuration Management

### Environment Variables

```env
# Server
PORT=11434
HOST=127.0.0.1

# Security
BEARER_TOKEN=required-secret-token

# Gemini CLI
GEMINI_CLI_PATH=gemini
GEMINI_CLI_TIMEOUT=30000

# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MS=60000

# Logging
LOG_LEVEL=info
LOG_FILE=logs/gemini-bridge.log
```

### Model Mappings

**File:** `config/models.json`

```json
{
  "gpt-3.5-turbo": "gemini-2.5-flash",
  "gpt-4": "gemini-2.5-pro",
  "gpt-4-turbo": "gemini-2.5-pro"
}
```

**Runtime Behavior:**
- Loaded once at startup
- Changes require server restart
- Missing file: uses default mappings
- Invalid JSON: uses default mappings

---

## Type System Architecture

**TypeScript Strict Mode:** Enabled

**Type Categories:**

1. **OpenAI API Types** (`src/types/index.ts`)
   - `ChatCompletionRequest`
   - `ChatCompletionResponse`
   - `ChatCompletionChunk`
   - `ModelsListResponse`
   - `OpenAIError`

2. **Gemini CLI Types**
   - `GeminiCLIConfig`
   - `CLIExecutionResult`

3. **Internal Types**
   - `RequestContext`
   - `LogEntry`
   - `AppConfig`
   - `ErrorDetails`

**Type Safety Guarantees:**
- No `any` types in production code
- Explicit function return types
- Strict null checks
- Unused variable detection

---

## Testing Strategy (Recommended)

### Unit Tests

**Coverage Targets:**
- `src/utils/prompt_builder.ts`: Message validation, prompt building
- `src/utils/error_handler.ts`: Error mapping, response formatting
- `src/config/index.ts`: Configuration loading, validation

### Integration Tests

**Scenarios:**
1. Full request/response cycle (non-streaming)
2. Streaming SSE format validation
3. Model mapping and fallback
4. Rate limiting behavior
5. Authentication failure cases

### E2E Tests

**Real CLI Execution:**
- Actual Gemini CLI integration
- UTF-8 encoding validation
- Timeout handling
- Error propagation

---

## Deployment Architecture

### Production Deployment

**Recommended Setup:**
```
┌─────────────┐
│   Nginx     │ ← HTTPS, reverse proxy
│  (Optional) │
└─────────────┘
       ↓
┌─────────────┐
│ GeminiBridge│ ← 127.0.0.1:11434
│   Server    │
└─────────────┘
       ↓
┌─────────────┐
│ Gemini CLI  │ ← Local installation
└─────────────┘
```

**Process Management:**
- PM2 or systemd for auto-restart
- Log rotation (Winston built-in)
- Health check monitoring (`/health`)

### Docker Deployment (Future)

**Considerations:**
- Gemini CLI installation in container
- Volume mounts for config and logs
- Environment variable injection
- Multi-stage builds for optimization

---

## Future Architecture Enhancements

### 1. True Real-Time Streaming

**Requirements:**
- Gemini CLI streaming output support
- Line-by-line parsing
- EventEmitter for chunk delivery

**Implementation:**
```typescript
// Revive GeminiStream class
stream.on('data', (chunk) => {
  res.write(`data: ${JSON.stringify(chunk)}\n\n`);
});
```

### 2. Request Queue System

**Design:**
- Priority queue for requests
- Concurrency limiting
- Fair scheduling algorithm

### 3. Distributed Rate Limiting

**Options:**
- Redis for shared state
- Token bucket algorithm
- Per-user quotas

### 4. Metrics & Monitoring

**Stack:**
- Prometheus for metrics
- Grafana for dashboards
- Alert manager for notifications

---

## References

- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Node.js child_process](https://nodejs.org/api/child_process.html)
- [Express.js Documentation](https://expressjs.com/)
- [Winston Logger](https://github.com/winstonjs/winston)
- [TypeScript Strict Mode](https://www.typescriptlang.org/tsconfig#strict)
