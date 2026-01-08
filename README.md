# GeminiBridge

OpenAI API-compatible proxy server for Google Gemini CLI. Enables browser extensions and applications designed for OpenAI API to work with local Gemini models.

## Features

- ✅ **OpenAI API Compatibility**: Full `/v1/models` and `/v1/chat/completions` support
- ✅ **Streaming Support**: SSE-compatible streaming responses (pseudo-streaming mode)
- ✅ **Model Mapping**: Automatic mapping from OpenAI models to Gemini models with fallback
- ✅ **Security**: Bearer token authentication, CORS, sandboxed CLI execution, and rate limiting
- ✅ **UTF-8 Support**: Full UTF-8 encoding support for international characters (Windows optimized)
- ✅ **Browser Extension Ready**: Works with Immersive Translate, ChatGPT Sider, and similar tools
- ✅ **Graceful Fallback**: Unmapped models automatically use `gemini-2.5-flash`

## Prerequisites

- Node.js 18+ and npm
- [Official Google Gemini CLI](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/call-gemini-using-cli) installed and configured
- ⚠️ **Important**: This project uses **plain text output mode** (not JSON output) and reads stdout directly
- ✅ **Compatible**: Works with any Gemini CLI version, including custom configurations with MCP servers

## Installation

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build
```

## Configuration

1. Create `.env` file from the example:

```bash
cp .env.example .env
```

2. Edit `.env` and set your configuration:

```env
# Server Configuration
PORT=11434
HOST=127.0.0.1

# Security (REQUIRED)
BEARER_TOKEN=your-secret-token-here

# Gemini CLI Configuration
GEMINI_CLI_PATH=gemini
GEMINI_CLI_TIMEOUT=30000

# Logging
LOG_LEVEL=info
LOG_RETENTION_DAYS=7

# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MS=60000
```

3. **Customize model mappings** (optional):

Edit `config/models.json` to map OpenAI model names to Gemini models:

```json
{
  "gpt-3.5-turbo": "gemini-2.5-flash",
  "gpt-4": "gemini-2.5-pro",
  "gpt-4-turbo": "gemini-2.5-pro"
}
```

**Fallback behavior**: Unmapped models automatically use `gemini-2.5-flash`.

## Usage

### Start the Server

**Production mode:**
```bash
npm start
```

**Development mode (with auto-reload):**
```bash
npm run dev
```

Server will start on `http://127.0.0.1:11434` by default.

### Test with cURL

**List available models:**
```bash
curl http://127.0.0.1:11434/v1/models \
  -H "Authorization: Bearer your-secret-token-here"
```

**Non-streaming chat completion:**
```bash
curl http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

**Streaming chat completion:**
```bash
curl -N http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "stream": true
  }'
```

**Note**: Streaming mode uses "pseudo-streaming" - the complete response is generated first, then sent as SSE chunks for OpenAI API compatibility.

### Browser Extension Integration

Configure your browser extension to use:

- **Base URL**: `http://127.0.0.1:11434`
- **API Key**: Your `BEARER_TOKEN` from `.env`

#### Immersive Translate
1. Open extension settings
2. Set "Custom API" or "OpenAI Compatible API"
3. Base URL: `http://127.0.0.1:11434`
4. API Key: Your bearer token

#### ChatGPT Sider
1. Open settings
2. Choose "Custom OpenAI API"
3. API Endpoint: `http://127.0.0.1:11434/v1/chat/completions`
4. API Key: Your bearer token

## API Endpoints

### GET /v1/models

Returns list of available models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {"id": "gpt-3.5-turbo", "object": "model"},
    {"id": "gpt-4", "object": "model"}
  ]
}
```

### POST /v1/chat/completions

Handles chat completion requests.

**Request body:**
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false
}
```

**Non-streaming response:**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-3.5-turbo",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello! How can I help?"},
    "finish_reason": "stop"
  }]
}
```

**Streaming response** (Server-Sent Events):
```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk",...}

data: [DONE]
```

### GET /health

Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-07T12:00:00.000Z",
  "version": "1.0.0"
}
```

## Security Considerations

1. **Bearer Token**: Always set a strong, random bearer token in production
2. **Localhost Only**: By default, server binds to `127.0.0.1` (localhost only)
3. **CORS**: Configured for browser extensions and localhost access
4. **CLI Sandbox**: Gemini CLI always runs with `--sandbox` flag
5. **Rate Limiting**: Prevents abuse (100 requests/minute by default)

## Troubleshooting

### Gemini CLI not found
```
Error: spawn gemini ENOENT
```
**Solution**: Install Gemini CLI or set correct path in `.env`:
```env
# Windows example (if using npm global install)
GEMINI_CLI_PATH=C:\Users\YourName\AppData\Roaming\npm\gemini.cmd

# Linux/macOS example
GEMINI_CLI_PATH=/usr/local/bin/gemini
```

### Authentication failed
```
{"error":{"message":"Invalid or missing bearer token"}}
```
**Solution**: Ensure you're sending the correct bearer token in the `Authorization` header.

### Rate limit exceeded
```
{"error":{"code":"rate_limit_exceeded"}}
```
**Solution**: Wait 1 minute or increase `RATE_LIMIT_MAX_REQUESTS` in `.env`.

### Timeout errors
```
{"error":{"code":"timeout"}}
```
**Solution**: Increase `GEMINI_CLI_TIMEOUT` in `.env` (default: 30000ms).

### UTF-8 encoding issues (Windows)
**Issue**: Characters appear garbled or malformed
**Solution**: The server automatically sets UTF-8 encoding on Windows. If issues persist:
1. Ensure your terminal uses UTF-8 encoding (`chcp 65001`)
2. Verify Gemini CLI outputs UTF-8 encoded text
3. Check logs in `logs/gemini-bridge.log` for debugging information

### Empty or invalid responses
**Issue**: `{"error":{"message":"Empty response from CLI"}}`
**Solution**:
1. Test Gemini CLI directly: `gemini -p "test" -m "gemini-2.5-flash" --sandbox`
2. Check CLI stdout is plain text (not JSON format)
3. Verify model name is correct in `config/models.json`
4. Review logs for detailed error messages

### Log file management
**Feature**: Daily rotating log files with automatic cleanup
- Log files are created daily with format: `gemini-bridge-YYYY-MM-DD.log` and `error-YYYY-MM-DD.log`
- Old log files are automatically compressed (gzip) to save disk space
- Logs older than `LOG_RETENTION_DAYS` (default: 7 days) are automatically deleted
- Configure retention period in `.env`: `LOG_RETENTION_DAYS=7`
- Log files location: `logs/` directory in the project root

## Development

```bash
# Run in development mode with auto-reload
npm run dev

# Build TypeScript
npm run build

# Run linter
npm run lint

# Format code
npm run format
```

## Project Structure

```
├── src/
│   ├── server.ts                 # Main application entry
│   ├── types/index.ts            # TypeScript type definitions
│   ├── config/index.ts           # Configuration loader
│   ├── utils/
│   │   ├── prompt_builder.ts     # OpenAI → Gemini prompt conversion
│   │   ├── logger.ts             # Winston logging
│   │   └── error_handler.ts      # Error formatting
│   ├── adapters/
│   │   └── gemini_cli.ts         # Gemini CLI interface
│   ├── middleware/
│   │   ├── auth.ts               # Bearer token validation
│   │   ├── cors.ts               # CORS configuration
│   │   ├── rate_limit.ts         # Rate limiting
│   │   └── request_logger.ts     # Request logging
│   └── routes/
│       ├── models.ts             # GET /v1/models
│       └── chat.ts               # POST /v1/chat/completions
├── config/
│   └── models.json               # Model mapping configuration
├── logs/                         # Log files (auto-created)
├── .env                          # Environment configuration
└── package.json
```

## License

MIT

## Support

For issues and questions, please check:
- [GUILD.md](docs/GUILD.md) - Architecture and design documentation
- [CLAUDE.md](CLAUDE.md) - Development guide for contributors
- GitHub Issues (if hosted on GitHub)
