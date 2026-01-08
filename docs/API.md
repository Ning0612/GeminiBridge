# GeminiBridge API Documentation

Complete API reference for GeminiBridge OpenAI-compatible proxy server.

## Base URL

```
http://127.0.0.1:11434
```

All endpoints require authentication unless otherwise specified.

---

## Authentication

All API requests (except `/health`) require Bearer token authentication.

### Header Format

```http
Authorization: Bearer YOUR_TOKEN_HERE
```

### Configuration

Set your bearer token in `.env`:

```env
BEARER_TOKEN=your-secret-token-here
```

### Error Response (401)

```json
{
  "error": {
    "message": "Invalid or missing bearer token",
    "type": "authentication_error",
    "code": "authentication_error"
  }
}
```

---

## Endpoints

### GET /health

Health check endpoint (no authentication required).

**Request:**
```bash
curl http://127.0.0.1:11434/health
```

**Response (200):**
```json
{
  "status": "ok",
  "timestamp": "2024-01-07T12:00:00.000Z",
  "version": "1.0.0"
}
```

---

### GET /v1/models

Returns list of available models based on `config/models.json` mappings.

**Request:**
```bash
curl http://127.0.0.1:11434/v1/models \
  -H "Authorization: Bearer your-token"
```

**Response (200):**
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-3.5-turbo",
      "object": "model"
    },
    {
      "id": "gpt-4",
      "object": "model"
    },
    {
      "id": "gpt-4-turbo",
      "object": "model"
    }
  ]
}
```

**Notes:**
- Model list reflects keys in `config/models.json`
- Models are mapped to Gemini CLI models
- Unmapped models automatically fallback to `gemini-2.5-flash`

---

### POST /v1/chat/completions

Chat completion endpoint supporting both streaming and non-streaming modes.

**Alternate path:** `/chat/completions` (without `/v1` prefix)

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | ✅ Yes | Model identifier (e.g., `gpt-3.5-turbo`) |
| `messages` | array | ✅ Yes | Array of message objects |
| `stream` | boolean | No | Enable streaming mode (default: `false`) |
| `temperature` | number | No | *Ignored (not passed to CLI)* |
| `top_p` | number | No | *Ignored (not passed to CLI)* |
| `max_tokens` | number | No | *Ignored (not passed to CLI)* |
| `n` | number | No | *Ignored (not passed to CLI)* |
| `stop` | string/array | No | *Ignored (not passed to CLI)* |
| `presence_penalty` | number | No | *Ignored (not passed to CLI)* |
| `frequency_penalty` | number | No | *Ignored (not passed to CLI)* |

**Message Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | ✅ Yes | One of: `system`, `user`, `assistant` |
| `content` | string | ✅ Yes | Message text content |

#### Non-Streaming Mode

**Request:**
```bash
curl http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ]
  }'
```

**Response (200):**
```json
{
  "id": "chatcmpl-a1b2c3d4",
  "object": "chat.completion",
  "created": 1704636000,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ]
}
```

#### Streaming Mode

**Request:**
```bash
curl -N http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Tell me a short story"}
    ],
    "stream": true
  }'
```

**Response (200):**

Server-Sent Events (SSE) format with multiple chunks:

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1704636000,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1704636000,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":"Once upon a time..."},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1704636000,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

**Chunk Object Structure:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Completion ID (format: `chatcmpl-{requestId}`) |
| `object` | string | Always `"chat.completion.chunk"` |
| `created` | number | Unix timestamp |
| `model` | string | Model identifier from request |
| `choices` | array | Array with single choice object |

**Choice Object (Streaming):**

| Field | Type | Description |
|-------|------|-------------|
| `index` | number | Always `0` |
| `delta` | object | Incremental content update |
| `finish_reason` | string/null | `null` during streaming, `"stop"` at end |

**Delta Object:**

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | `"assistant"` (only in first chunk) |
| `content` | string | Text content (in subsequent chunks) |

**Note:** Streaming mode uses "pseudo-streaming" - the complete response is generated first, then sent as SSE chunks for OpenAI API compatibility.

---

## Error Responses

All errors follow OpenAI API error format:

```json
{
  "error": {
    "message": "Error description",
    "type": "error_type",
    "code": "error_code",
    "param": "field_name"
  }
}
```

### Error Types

| HTTP Status | Error Code | Type | Description |
|-------------|------------|------|-------------|
| 400 | `invalid_request_error` | `invalid_request_error` | Missing or invalid request fields |
| 401 | `authentication_error` | `authentication_error` | Invalid or missing bearer token |
| 404 | `not_found` | `invalid_request_error` | Route not found |
| 429 | `rate_limit_exceeded` | `rate_limit_exceeded` | Too many requests (>100/min) |
| 500 | `model_error` | `api_error` | Gemini CLI execution failed |
| 500 | `invalid_response_format` | `api_error` | Failed to parse CLI output |
| 500 | `internal_error` | `api_error` | Internal server error |
| 504 | `timeout` | `api_error` | CLI execution timeout |

### Example Error Responses

**Missing required field (400):**
```json
{
  "error": {
    "message": "Missing required field: model",
    "type": "invalid_request_error",
    "code": "invalid_request_error",
    "param": "model"
  }
}
```

**Rate limit exceeded (429):**
```json
{
  "error": {
    "message": "Rate limit exceeded",
    "type": "rate_limit_exceeded",
    "code": "rate_limit_exceeded"
  }
}
```

**CLI execution failed (500):**
```json
{
  "error": {
    "message": "Gemini CLI execution failed: exit code 1",
    "type": "api_error",
    "code": "model_error"
  }
}
```

**Timeout (504):**
```json
{
  "error": {
    "message": "Execution timeout",
    "type": "api_error",
    "code": "timeout"
  }
}
```

---

## Model Mapping

Models are mapped in `config/models.json`:

```json
{
  "gpt-3.5-turbo": "gemini-2.5-flash",
  "gpt-3.5-turbo-16k": "gemini-2.5-flash",
  "gpt-4": "gemini-2.5-pro",
  "gpt-4-turbo": "gemini-2.5-pro",
  "gpt-4-turbo-preview": "gemini-2.5-pro",
  "gpt-4o": "gemini-2.5-pro",
  "gpt-4o-mini": "gemini-2.5-flash"
}
```


### Fallback Behavior

If a requested model is **not** in `config/models.json`, it automatically falls back to:

```
gemini-2.5-flash
```

**Example:**
```bash
# Request with unmapped model
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Authorization: Bearer token" \
  -d '{"model":"gpt-99-ultra","messages":[...]}'

# Executes using: gemini-2.5-flash
```

---

## Rate Limiting

**Default limits:**
- 100 requests per 60 seconds
- Tracked per client IP address

**Configuration** (`.env`):
```env
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MS=60000
```

**Response when exceeded:**
```json
{
  "error": {
    "message": "Rate limit exceeded",
    "type": "rate_limit_exceeded",
    "code": "rate_limit_exceeded"
  }
}
```

**HTTP Status:** `429 Too Many Requests`

---

## CORS Configuration

CORS is configured to support browser extensions:

**Allowed origins:**
- `http://localhost:*`
- `http://127.0.0.1:*`
- `chrome-extension://*`
- `moz-extension://*`

**Allowed methods:**
- `GET`, `POST`, `OPTIONS`

**Allowed headers:**
- `Content-Type`
- `Authorization`

---

## Request/Response Examples

### Example 1: Simple Chat

**Request:**
```bash
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-token" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ]
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1704636000,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I assist you today?"
      },
      "finish_reason": "stop"
    }
  ]
}
```

### Example 2: Multi-turn Conversation

**Request:**
```bash
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-token" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "system", "content": "You are a helpful math tutor."},
      {"role": "user", "content": "What is 2+2?"},
      {"role": "assistant", "content": "2+2 equals 4."},
      {"role": "user", "content": "What about 3+3?"}
    ]
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-def456",
  "object": "chat.completion",
  "created": 1704636100,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "3+3 equals 6."
      },
      "finish_reason": "stop"
    }
  ]
}
```

### Example 3: Streaming Response

**Request:**
```bash
curl -N -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-token" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Count to 3"}
    ],
    "stream": true
  }'
```

**Response (SSE stream):**
```
data: {"id":"chatcmpl-ghi789","object":"chat.completion.chunk","created":1704636200,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-ghi789","object":"chat.completion.chunk","created":1704636200,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{"content":"1, 2, 3"},"finish_reason":null}]}

data: {"id":"chatcmpl-ghi789","object":"chat.completion.chunk","created":1704636200,"model":"gpt-3.5-turbo","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

---

## Implementation Details

### Prompt Building

Messages are converted to Gemini CLI format using this pattern:

```
[System]
system message content

[User]
user message content

[Assistant]
assistant message content
```

- Conversation history limited to last 20 messages
- Messages validated for required `role` and `content` fields
- Empty messages rejected

### CLI Execution

**Command pattern:**
```bash
gemini -m <model> --sandbox
# Prompt sent via stdin
```

**Key behaviors:**
- Always uses `--sandbox` flag for security
- Prompt passed via stdin (UTF-8 encoded)
- Stdout captured as plain text (no JSON parsing)
- Temporary working directory created per request
- Timeout enforced (default: 30 seconds)
- Uses 'close' event to ensure stdout fully flushed

### UTF-8 Support

- Full UTF-8 encoding support for international characters
- Windows console automatically set to UTF-8 (code page 65001)
- Explicit UTF-8 buffer handling in stdin/stdout
- Debug logging includes hex dumps for encoding verification

---

## Client Integration

### JavaScript/TypeScript

```typescript
const response = await fetch('http://127.0.0.1:11434/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token'
  },
  body: JSON.stringify({
    model: 'gpt-3.5-turbo',
    messages: [
      { role: 'user', content: 'Hello!' }
    ]
  })
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

### Python

```python
import requests

response = requests.post(
    'http://127.0.0.1:11434/v1/chat/completions',
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer your-token'
    },
    json={
        'model': 'gpt-3.5-turbo',
        'messages': [
            {'role': 'user', 'content': 'Hello!'}
        ]
    }
)

print(response.json()['choices'][0]['message']['content'])
```

### Browser Extension

**Configuration:**
- Base URL: `http://127.0.0.1:11434`
- API Key: Your bearer token from `.env`
- Path: Use standard OpenAI paths (`/v1/chat/completions`)

**Example (Immersive Translate):**
1. Settings → Custom API
2. API URL: `http://127.0.0.1:11434`
3. API Key: `your-bearer-token`
4. Model: `gpt-3.5-turbo` (or any mapped model)

---

## Logging

All requests are logged to:
- Console (development mode)
- `logs/gemini-bridge.log` (JSON format)
- `logs/error.log` (errors only)

**Log fields:**
- `requestId`: Unique UUID per request
- `clientIp`: Client IP address
- `userAgent`: Client user agent
- `model`: Requested model
- `mappedModel`: Actual Gemini model used
- `stream`: Boolean indicating streaming mode
- `exitCode`: CLI process exit code
- `stderr`: CLI error output
- `latency`: Request duration in ms
- `error`: Error message (if failed)

---

## See Also

- [README.md](../README.md) - Setup and usage guide
- [CLAUDE.md](../CLAUDE.md) - Development guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture documentation

