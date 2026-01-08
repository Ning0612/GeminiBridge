# GeminiBridge

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**GeminiBridge** is an OpenAI API-compatible proxy server that bridges the gap between applications built for OpenAI's API and Google's Gemini models. It translates OpenAI-formatted chat completion requests into Gemini CLI commands, enabling seamless integration without code changes.

## ✨ Features

- 🔄 **OpenAI API Compatibility** - Drop-in replacement for OpenAI's chat completion endpoints
- 🚀 **High Performance** - Async architecture with configurable concurrency control
- 🔒 **Enterprise Security** - Bearer token authentication, rate limiting, and request validation
- 📊 **Production Ready** - Structured JSON logging, automatic retry logic, and health monitoring
- 🐳 **Docker Support** - Sandboxed CLI execution with automatic conflict resolution
- 🌐 **CORS Enabled** - Cross-origin resource sharing for web applications
- ⚡ **Streaming Support** - Server-sent events (SSE) for real-time responses
- 📝 **Comprehensive Logging** - Daily rotation, automatic cleanup, and sensitive data masking

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
│ Application │
└──────┬──────┘
       │ OpenAI API Format
       │ (HTTP/JSON)
       ▼
┌──────────────────────────────────────┐
│         GeminiBridge Server          │
│  ┌────────────────────────────────┐  │
│  │   Authentication Middleware    │  │
│  └────────────┬───────────────────┘  │
│               ▼                      │
│  ┌────────────────────────────────┐  │
│  │   Rate Limiting Middleware     │  │
│  └────────────┬───────────────────┘  │
│               ▼                      │
│  ┌────────────────────────────────┐  │
│  │     Request Validator          │  │
│  └────────────┬───────────────────┘  │
│               ▼                      │
│  ┌────────────────────────────────┐  │
│  │      Queue Manager             │  │
│  │  (Concurrency Control)         │  │
│  └────────────┬───────────────────┘  │
│               ▼                      │
│  ┌────────────────────────────────┐  │
│  │     Gemini CLI Adapter         │  │
│  │  (with Retry Logic)            │  │
│  └────────────┬───────────────────┘  │
└───────────────┼──────────────────────┘
                │ Gemini CLI Protocol
                ▼
       ┌─────────────────┐
       │   Gemini CLI    │
       │  (Sandboxed)    │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  Gemini Models  │
       │   (Google AI)   │
       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** installed
- **Gemini CLI** installed and configured ([Installation Guide](https://geminicli.com/))
- **Docker** (required for sandboxed execution)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/GeminiBridge.git
   cd GeminiBridge
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/Mac
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   # Copy example configuration
   # Windows:
   copy .env.example .env
   # Linux/Mac:
   cp .env.example .env

   # Generate secure bearer token
   python scripts/generate_token.py

   # Edit .env and add your token
   # Update GEMINI_CLI_PATH if needed
   ```

5. **Run security check**
   ```bash
   python scripts/check_security.py
   ```

6. **Start the server**
   ```bash
   python main.py
   ```

The server will start on `http://127.0.0.1:11434` by default.

## 📖 Usage

### Basic Example

```python
import requests

url = "http://127.0.0.1:11434/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_TOKEN_HERE"
}
data = {
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

### Using OpenAI Python Library

```python
from openai import OpenAI

# Point to GeminiBridge server
client = OpenAI(
    api_key="YOUR_TOKEN_HERE",
    base_url="http://127.0.0.1:11434/v1"
)

# Use exactly like OpenAI API
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

### Streaming Responses

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_TOKEN_HERE",
    base_url="http://127.0.0.1:11434/v1"
)

stream = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## 🔑 Model Mapping

GeminiBridge automatically maps OpenAI model names to Gemini models:

| OpenAI Model | Gemini Model |
|--------------|--------------|
| `gpt-3.5-turbo` | `gemini-2.5-flash` |
| `gpt-3.5-turbo-16k` | `gemini-2.5-flash` |
| `gpt-4` | `gemini-2.5-pro` |
| `gpt-4-turbo` | `gemini-2.5-pro` |
| `gpt-4-turbo-preview` | `gemini-2.5-pro` |
| `gpt-4o` | `gemini-2.5-pro` |
| `gpt-4o-mini` | `gemini-2.5-flash` |

You can also directly request Gemini models:
```json
{
    "model": "gemini-2.5-pro",
    "messages": [...]
}
```

Model mappings are configured in `config/models.json`.

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | Server port | `11434` | No |
| `HOST` | Server host | `127.0.0.1` | No |
| `BEARER_TOKEN` | Authentication token | - | **Yes** |
| `GEMINI_CLI_PATH` | Path to Gemini CLI | `gemini` | No |
| `GEMINI_CLI_TIMEOUT` | CLI timeout (seconds) | `30` | No |
| `CLI_MAX_RETRIES` | Max retry attempts for Docker conflicts | `3` | No |
| `MAX_CONCURRENT_REQUESTS` | Max concurrent CLI processes | `5` | No |
| `QUEUE_TIMEOUT` | Queue timeout (seconds) | `30` | No |
| `RATE_LIMIT_MAX_REQUESTS` | Max requests per window | `100` | No |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `LOG_RETENTION_DAYS` | Log retention period | `7` | No |
| `DEBUG` | Enable debug mode | `false` | No |

See [`.env.example`](.env.example) for detailed configuration options.

**Note**: CORS is currently hardcoded in the application. To customize CORS settings, modify `src/app.py`.

### Security Best Practices

1. **Generate a strong bearer token**
   ```bash
   python scripts/generate_token.py
   ```

2. **Run security checks**
   ```bash
   python scripts/check_security.py
   ```

3. **Use HTTPS in production** - Deploy behind a reverse proxy with TLS enabled

## 📊 API Endpoints

### Health Check
```http
GET /health
```
Returns server status and queue statistics.

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

### List Models
```http
GET /v1/models
Authorization: Bearer YOUR_TOKEN
```
Returns list of available models.

### Chat Completions
```http
POST /v1/chat/completions
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 1000
}
```

**Response:**
```json
{
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "gpt-4",
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "Hello! How can I help you today?"
        },
        "finish_reason": "stop"
    }]
}
```

See [API Documentation](docs/API.md) for complete API reference.

## 🛠️ Development

### Project Structure

```
GeminiBridge/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment configuration template
├── CLAUDE.md              # AI assistant guidance
├── config/
│   └── models.json        # Model mapping configuration
├── src/
│   ├── __init__.py
│   ├── app.py             # FastAPI application
│   ├── config.py          # Configuration loader
│   ├── gemini_cli.py      # Gemini CLI adapter
│   ├── queue_manager.py   # Concurrency control
│   ├── logger.py          # Logging system
│   └── prompt_builder.py  # Prompt formatter
├── scripts/
│   ├── generate_token.py  # Token generator
│   └── check_security.py  # Security checker
├── docs/
│   ├── INDEX.md           # Documentation index
│   ├── API.md             # API documentation
│   ├── ARCHITECTURE.md    # Architecture guide
│   ├── DEPLOYMENT.md      # Deployment guide
│   ├── SECURITY.md        # Security documentation
│   └── DEVELOPMENT.md     # Development guide
└── logs/                  # Generated log files
```

### Running Tests

```bash
# Syntax check
python -m py_compile src/app.py

# Compile all source files
python -m compileall src/

# Security audit
pip install pip-audit
pip-audit

# Test endpoints
curl http://127.0.0.1:11434/health
```

### Code Quality

```bash
# Format code
pip install black
black src/

# Type checking
pip install mypy
mypy src/

# Linting
pip install ruff
ruff check src/
```

## 🐳 Docker Deployment

### Using Docker Compose

```yaml
version: '3.8'
services:
  geminibridge:
    build: .
    ports:
      - "11434:11434"
    environment:
      - BEARER_TOKEN=${BEARER_TOKEN}
      - GEMINI_CLI_PATH=/usr/local/bin/gemini
    volumes:
      - ./logs:/app/logs
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed deployment instructions.

## 📚 Documentation

- [API Reference](docs/API.md) - Complete API documentation
- [Architecture Guide](docs/ARCHITECTURE.md) - System architecture and design
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment instructions
- [Security Guide](docs/SECURITY.md) - Security best practices and guidelines
- [Development Guide](docs/DEVELOPMENT.md) - Development workflow and guidelines

## 🔒 Security Features

- **Bearer Token Authentication** - Timing-safe token comparison
- **Rate Limiting** - Per-IP sliding window rate limiting
- **Request Validation** - Comprehensive input validation and sanitization
- **Sandboxed Execution** - Docker-based CLI isolation
- **Sensitive Data Masking** - Automatic masking in logs
- **CORS Protection** - Configurable cross-origin resource sharing
- **DoS Protection** - Request size limits and queue timeouts

See [Security Documentation](docs/SECURITY.md) for detailed security information.

## 🐛 Troubleshooting

### Common Issues

**CLI Execution Errors**
- Verify `GEMINI_CLI_PATH` points to the correct executable
- Check Docker is running for sandboxed execution
- Review logs in `logs/` directory

**Authentication Failures**
- Ensure `BEARER_TOKEN` matches between client and server
- Check token is properly set in Authorization header

**Performance Issues**
- Increase `MAX_CONCURRENT_REQUESTS` for higher throughput
- Adjust `QUEUE_TIMEOUT` for long-running requests
- Monitor queue statistics via `/health` endpoint

**For more help**, check the server logs or open an issue on GitHub.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Google Generative AI](https://ai.google.dev/) - Gemini models
- [OpenAI](https://openai.com/) - API specification

## 📞 Support

- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/GeminiBridge/issues)

---

**Made with ❤️ by the GeminiBridge Team**
