# API Reference

Complete API documentation for GeminiBridge v2.0.0

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [List Models](#list-models)
  - [Chat Completions](#chat-completions)
- [Request/Response Formats](#requestresponse-formats)
- [Code Examples](#code-examples)

## Overview

GeminiBridge implements the OpenAI Chat Completions API specification, providing compatibility with OpenAI client libraries and tools. The API supports core chat completion features including streaming responses, though some optional fields (such as token usage statistics) may not be included in responses.

**Base URL:** `http://127.0.0.1:11434/v1`

**API Version:** v1 (OpenAI compatible)

**Supported Content Types:**
- `application/json`

**Supported Authentication:**
- Bearer Token

## Authentication

All API requests (except `/health`) require authentication using Bearer tokens.

### Request Header

```http
Authorization: Bearer YOUR_TOKEN_HERE
```

### Authentication Flow

1. Client includes Bearer token in `Authorization` header
2. Server validates token using timing-safe comparison
3. Request proceeds if token matches, otherwise returns 401

### Error Responses

**Missing Authorization Header**
```json
{
    "error": {
        "message": "Missing authorization header",
        "type": "authentication_error",
        "code": "missing_auth_header"
    }
}
```
Status: `401 Unauthorized`

**Invalid Authorization Format**
```json
{
    "error": {
        "message": "Invalid authorization header format",
        "type": "authentication_error",
        "code": "invalid_auth_header"
    }
}
```
Status: `401 Unauthorized`

**Invalid Token**
```json
{
    "error": {
        "message": "Invalid bearer token",
        "type": "authentication_error",
        "code": "invalid_token"
    }
}
```
Status: `401 Unauthorized`

## Rate Limiting

GeminiBridge implements per-IP sliding window rate limiting to prevent abuse.

### Default Limits

- **Max Requests:** 100 requests per window
- **Window Size:** 60 seconds
- **Scope:** Per client IP address

### Rate Limit Headers

```http
X-RateLimit-Remaining: 95
```

### Rate Limit Error

```json
{
    "error": {
        "message": "Rate limit exceeded. Please try again later.",
        "type": "rate_limit_exceeded",
        "code": "rate_limit_exceeded"
    }
}
```
Status: `429 Too Many Requests`

### Configuration

Rate limits can be configured via environment variables:
```bash
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

## Error Handling

### Error Response Format

All errors follow the OpenAI error format:

```json
{
    "error": {
        "message": "Human-readable error description",
        "type": "error_type",
        "code": "error_code"
    }
}
```

### Error Types

| Type | Description | HTTP Status |
|------|-------------|-------------|
| `authentication_error` | Authentication failed | 401 |
| `invalid_request_error` | Request validation failed | 400 |
| `rate_limit_exceeded` | Too many requests | 429 |
| `api_error` | Server or model error | 500 |
| `timeout_error` | Request timeout | 504 |

### Common Error Codes

| Code | Description |
|------|-------------|
| `missing_auth_header` | No Authorization header provided |
| `invalid_auth_header` | Authorization header format invalid |
| `invalid_token` | Bearer token does not match |
| `invalid_request` | Request body validation failed |
| `missing_parameter` | Required parameter missing |
| `model_error` | Gemini CLI execution failed |
| `timeout` | CLI execution timeout |

## Endpoints

### Health Check

Check server status and queue statistics.

**Endpoint:** `GET /health`

**Authentication:** Not required

**Request:**
```http
GET /health HTTP/1.1
Host: 127.0.0.1:11434
```

**Response:**
```json
{
    "status": "healthy",
    "service": "GeminiBridge Python",
    "version": "2.0.0",
    "queue": {
        "active_requests": 2,
        "queued_requests": 0,
        "total_processed": 1523,
        "average_wait_time_ms": 45,
        "max_concurrent": 5
    }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Server health status (always "healthy") |
| `service` | string | Service name |
| `version` | string | Service version |
| `queue.active_requests` | integer | Currently executing requests |
| `queue.queued_requests` | integer | Requests waiting in queue |
| `queue.total_processed` | integer | Total requests processed since startup |
| `queue.average_wait_time_ms` | integer | Average queue wait time in milliseconds |
| `queue.max_concurrent` | integer | Maximum concurrent request limit |

**Status Codes:**
- `200 OK` - Server is healthy

---

### List Models

Retrieve list of available models.

**Endpoint:** `GET /v1/models`

**Authentication:** Required

**Request:**
```http
GET /v1/models HTTP/1.1
Host: 127.0.0.1:11434
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
    "object": "list",
    "data": [
        {
            "id": "gpt-3.5-turbo",
            "object": "model"
        },
        {
            "id": "gpt-3.5-turbo-16k",
            "object": "model"
        },
        {
            "id": "gpt-4",
            "object": "model"
        },
        {
            "id": "gpt-4-turbo",
            "object": "model"
        },
        {
            "id": "gpt-4-turbo-preview",
            "object": "model"
        },
        {
            "id": "gpt-4o",
            "object": "model"
        },
        {
            "id": "gpt-4o-mini",
            "object": "model"
        }
    ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `object` | string | Always "list" |
| `data` | array | Array of model objects |
| `data[].id` | string | Model identifier |
| `data[].object` | string | Always "model" |

**Status Codes:**
- `200 OK` - Successfully retrieved model list
- `401 Unauthorized` - Authentication failed

---

### Chat Completions

Create a chat completion using OpenAI-compatible format.

**Endpoint:** `POST /v1/chat/completions`

**Authentication:** Required

**Request Headers:**
```http
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN
```

#### Request Body

```json
{
    "model": "gpt-4",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "What is the capital of France?"
        }
    ],
    "stream": false,
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 1000
}
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model to use (e.g., "gpt-4", "gemini-2.5-pro") |
| `messages` | array | Yes | Array of message objects |
| `messages[].role` | string | Yes | Message role: "system", "user", or "assistant" |
| `messages[].content` | string | Yes | Message content text |
| `stream` | boolean | No | Enable streaming (default: false) |
| `temperature` | float | No | Sampling temperature 0-2 (currently ignored) |
| `top_p` | float | No | Nucleus sampling (currently ignored) |
| `max_tokens` | integer | No | Max tokens to generate (currently ignored) |

**Validation Rules:**

- `messages` must be non-empty array
- Maximum 100 messages per request
- Maximum 100,000 characters per message
- `role` must be one of: "system", "user", "assistant"
- `content` must be non-empty string

#### Non-Streaming Response

**Response:**
```json
{
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "gpt-4",
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique completion identifier |
| `object` | string | Always "chat.completion" |
| `created` | integer | Unix timestamp of creation |
| `model` | string | Model used for completion |
| `choices` | array | Array of completion choices |
| `choices[].index` | integer | Choice index (always 0) |
| `choices[].message` | object | Generated message |
| `choices[].message.role` | string | Always "assistant" |
| `choices[].message.content` | string | Generated response text |
| `choices[].finish_reason` | string | Completion reason (always "stop") |

#### Streaming Response

When `stream: true`, server returns Server-Sent Events (SSE).

**Response Headers:**
```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Stream Events:**

1. **Initial Chunk** (role)
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

```

2. **Content Chunk** (response text)
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"The capital of France is Paris."},"finish_reason":null}]}

```

3. **Final Chunk** (completion)
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

```

4. **Done Marker**
```
data: [DONE]

```

**Streaming Chunk Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique completion identifier |
| `object` | string | Always "chat.completion.chunk" |
| `created` | integer | Unix timestamp |
| `model` | string | Model identifier |
| `choices[].delta` | object | Incremental message delta |
| `choices[].delta.role` | string | Role (only in first chunk) |
| `choices[].delta.content` | string | Content fragment |
| `choices[].finish_reason` | string | Completion reason (only in final chunk) |

**Status Codes:**
- `200 OK` - Successfully generated completion
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication failed
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server or model error
- `504 Gateway Timeout` - CLI execution timeout

## Request/Response Formats

### Message Format

Messages follow the OpenAI format:

```json
{
    "role": "system|user|assistant",
    "content": "message text"
}
```

### Conversation Example

```json
{
    "model": "gpt-4",
    "messages": [
        {
            "role": "system",
            "content": "You are a Python programming expert."
        },
        {
            "role": "user",
            "content": "How do I read a file in Python?"
        },
        {
            "role": "assistant",
            "content": "You can read a file using the open() function..."
        },
        {
            "role": "user",
            "content": "Can you show me an example?"
        }
    ]
}
```

## Code Examples

### Python (requests)

```python
import requests

url = "http://127.0.0.1:11434/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_TOKEN"
}
data = {
    "model": "gpt-4",
    "messages": [
        {"role": "user", "content": "Hello!"}
    ]
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
print(result["choices"][0]["message"]["content"])
```

### Python (OpenAI Library)

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TOKEN",
    base_url="http://127.0.0.1:11434/v1"
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://127.0.0.1:11434/v1/chat/completions', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_TOKEN'
    },
    body: JSON.stringify({
        model: 'gpt-4',
        messages: [
            { role: 'user', content: 'Hello!' }
        ]
    })
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

### JavaScript (OpenAI Library)

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: 'YOUR_TOKEN',
    baseURL: 'http://127.0.0.1:11434/v1'
});

const response = await client.chat.completions.create({
    model: 'gpt-4',
    messages: [
        { role: 'user', content: 'Hello!' }
    ]
});

console.log(response.choices[0].message.content);
```

### cURL

```bash
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Streaming with Python

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TOKEN",
    base_url="http://127.0.0.1:11434/v1"
)

stream = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Error Handling

```python
from openai import OpenAI, AuthenticationError, RateLimitError

client = OpenAI(
    api_key="YOUR_TOKEN",
    base_url="http://127.0.0.1:11434/v1"
)

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)

except AuthenticationError as e:
    print(f"Authentication failed: {e}")

except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")

except Exception as e:
    print(f"Error: {e}")
```

## Model Mapping Reference

| OpenAI Model | Gemini Model | Use Case |
|--------------|--------------|----------|
| `gpt-3.5-turbo` | `gemini-2.5-flash` | Fast, lightweight tasks |
| `gpt-3.5-turbo-16k` | `gemini-2.5-flash` | Longer context |
| `gpt-4` | `gemini-2.5-pro` | Complex reasoning |
| `gpt-4-turbo` | `gemini-2.5-pro` | Advanced capabilities |
| `gpt-4-turbo-preview` | `gemini-2.5-pro` | Turbo preview version |
| `gpt-4o` | `gemini-2.5-pro` | Latest optimized |
| `gpt-4o-mini` | `gemini-2.5-flash` | Efficient mini model |

You can also use Gemini models directly:
- `gemini-2.5-flash`
- `gemini-2.5-pro`
- `gemini-1.5-flash`
- `gemini-1.5-pro`

## Limits and Quotas

### Request Limits

- **Max messages per request:** 100
- **Max characters per message:** 100,000
- **Max message history:** Last 20 messages used
- **Request timeout:** 30 seconds (configurable)
- **Queue timeout:** 30 seconds (configurable)

### Concurrency Limits

- **Max concurrent requests:** 5 (configurable)
- **Queue size:** Unlimited (limited by timeout)

### Rate Limits

- **Default:** 100 requests per 60 seconds per IP
- **Configurable:** Via `RATE_LIMIT_MAX_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`

## Best Practices

1. **Always handle errors** - Use try-catch for robust error handling
2. **Implement retry logic** - Handle rate limits with exponential backoff
3. **Use streaming for long responses** - Better user experience
4. **Validate input** - Check message format before sending
5. **Monitor rate limits** - Track `X-RateLimit-Remaining` header
6. **Secure your token** - Never expose bearer token in client-side code
7. **Use health checks** - Monitor server status before requests
8. **Log failures** - Track errors for debugging and monitoring

## Support

For API-related issues or questions:

- Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
- Review server logs in `logs/` directory
- Submit an issue on [GitHub](https://github.com/yourusername/GeminiBridge/issues)
