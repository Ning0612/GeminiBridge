# GeminiBridge Documentation Index

Complete documentation overview for GeminiBridge OpenAI API-compatible proxy server.

## Quick Start

**New to GeminiBridge?** Start here:
1. [README.md](../README.md) - Installation, configuration, and usage
2. [API.md](API.md) - API reference and examples
3. [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design

## Documentation Structure

### 📘 User Documentation

#### [README.md](../README.md)
**For end users and system administrators**

- Features and capabilities overview
- Installation and setup instructions
- Configuration guide (`.env` and `config/models.json`)
- Usage examples with cURL
- Browser extension integration (Immersive Translate, ChatGPT Sider)
- Troubleshooting common issues
- Deployment guides (PM2, systemd, Docker)
- Security considerations

**Start here if you want to:**
- Install and run GeminiBridge
- Configure browser extensions
- Deploy to production
- Troubleshoot issues

---

#### [API.md](API.md)
**For API consumers and integration developers**

- Complete API reference for all endpoints
- Request/response formats with examples
- Error codes and handling
- Model mapping and fallback behavior
- Rate limiting specifications
- CORS configuration
- Client integration examples (JavaScript, Python, Browser Extensions)

**Start here if you want to:**
- Integrate GeminiBridge into your application
- Understand API behavior and responses
- Debug API-related issues
- Build custom clients

---

#### [ARCHITECTURE.md](ARCHITECTURE.md)
**For developers, architects, and contributors**

- Comprehensive system architecture and design philosophy
- Component-level implementation details
- Data flow diagrams (streaming and non-streaming)
- Security architecture and threat mitigation
- Performance considerations and optimization strategies
- Error handling strategies
- Type system architecture
- Testing strategies (unit, integration, E2E)
- Deployment architecture
- Code organization and structure
- Development guidelines
- Future enhancement roadmap

**Start here if you want to:**
- Understand system architecture and design decisions
- Contribute to the project
- Extend or modify functionality
- Evaluate security posture
- Optimize performance
- Design integrations

---

## Quick Reference

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables and runtime configuration |
| `config/models.json` | OpenAI to Gemini model mappings |
| `package.json` | Project dependencies and scripts |
| `tsconfig.json` | TypeScript compiler configuration |

### Source Code Structure

```
src/
├── server.ts                 # Main application entry point
├── types/index.ts            # TypeScript type definitions
├── config/index.ts           # Configuration loader
├── adapters/
│   └── gemini_cli.ts         # Gemini CLI execution interface
├── middleware/
│   ├── auth.ts               # Bearer token authentication
│   ├── cors.ts               # CORS configuration
│   ├── rate_limit.ts         # Rate limiting (sliding window)
│   └── request_logger.ts     # Request logging and context
├── routes/
│   ├── models.ts             # GET /v1/models endpoint
│   └── chat.ts               # POST /v1/chat/completions endpoint
└── utils/
    ├── cli_queue.ts          # CLI concurrency control
    ├── error_handler.ts      # OpenAI-compatible error formatting
    ├── logger.ts             # Winston logger with daily rotation
    └── prompt_builder.ts     # OpenAI → Gemini prompt conversion
```

### Key Features

| Feature | Configuration | Documentation |
|---------|---------------|---------------|
| **OpenAI API Compatibility** | `config/models.json` | [API.md](API.md) |
| **Streaming (Pseudo)** | `stream: true` in request | [ARCHITECTURE.md](ARCHITECTURE.md#streaming-request-pseudo-streaming) |
| **Rate Limiting** | `RATE_LIMIT_*` in `.env` | [README.md](../README.md#security-considerations) |
| **Concurrency Control** | `MAX_CONCURRENT_REQUESTS` in `.env` | [ARCHITECTURE.md](ARCHITECTURE.md#resource-management) |
| **Log Rotation** | `LOG_RETENTION_DAYS` in `.env` | [README.md](../README.md#log-file-management) |
| **Bearer Token Auth** | `BEARER_TOKEN` in `.env` | [API.md](API.md#authentication) |
| **Model Fallback** | Automatic to `gemini-2.5-flash` | [README.md](../README.md#configuration) |
| **UTF-8 Support** | Automatic (Windows optimized) | [README.md](../README.md#utf-8-encoding-issues-windows) |

### Common Tasks

| Task | Documentation |
|------|---------------|
| Install and configure | [README.md - Installation](../README.md#installation) |
| Test with cURL | [README.md - Test with cURL](../README.md#test-with-curl) |
| Configure browser extension | [README.md - Browser Extension Integration](../README.md#browser-extension-integration) |
| Deploy to production | [README.md - Deployment](../README.md#deployment) |
| Debug Gemini CLI issues | [README.md - Troubleshooting](../README.md#gemini-cli-not-found) |
| Understand API errors | [API.md - Error Responses](API.md#error-responses) |
| Modify model mappings | [README.md - Configuration](../README.md#configuration) |
| Understand streaming | [ARCHITECTURE.md - Streaming](ARCHITECTURE.md#streaming-request-pseudo-streaming) |
| Security hardening | [README.md - Security](../README.md#security-considerations) |
| Performance tuning | [ARCHITECTURE.md - Performance](ARCHITECTURE.md#performance-considerations) |
| System architecture | [ARCHITECTURE.md - Component Architecture](ARCHITECTURE.md#component-architecture) |

### API Endpoints Reference

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/health` | GET | No | Health check with system stats |
| `/v1/models` | GET | Yes | List available models |
| `/v1/chat/completions` | POST | Yes | Chat completion (streaming/non-streaming) |
| `/chat/completions` | POST | Yes | Alias for `/v1/chat/completions` |

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `11434` | HTTP server port |
| `HOST` | `127.0.0.1` | Server bind address |
| `BEARER_TOKEN` | *(required)* | API authentication token |
| `GEMINI_CLI_TIMEOUT` | `30000` | CLI execution timeout (ms) |
| `LOG_LEVEL` | `info` | Log level (error/warn/info/debug) |
| `LOG_RETENTION_DAYS` | `7` | Log file retention period |
| `DEBUG` | `false` | Enable debug mode |
| `RATE_LIMIT_MAX_REQUESTS` | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW_MS` | `60000` | Rate limit window (ms) |
| `MAX_CONCURRENT_REQUESTS` | `5` | Max concurrent CLI processes |
| `QUEUE_TIMEOUT` | `30000` | Queue timeout (ms) |

## Troubleshooting Guide

| Issue | Solution | Documentation |
|-------|----------|---------------|
| CLI not found | Install Gemini CLI globally (path hard-coded to 'gemini' to prevent CLI from reading unintended files) | [README.md - Troubleshooting](../README.md#gemini-cli-not-found) |
| Authentication failed | Check `BEARER_TOKEN` in request header | [API.md - Authentication](API.md#authentication) |
| Rate limit exceeded | Wait 60s or increase `RATE_LIMIT_MAX_REQUESTS` | [README.md - Troubleshooting](../README.md#rate-limit-exceeded) |
| Timeout errors | Increase `GEMINI_CLI_TIMEOUT` | [README.md - Troubleshooting](../README.md#timeout-errors) |
| UTF-8 encoding issues | Server auto-configures, check terminal settings | [README.md - Troubleshooting](../README.md#utf-8-encoding-issues-windows) |
| Empty responses | Test CLI directly, check logs | [README.md - Troubleshooting](../README.md#empty-or-invalid-responses) |
| Concurrency issues | Adjust `MAX_CONCURRENT_REQUESTS` | [ARCHITECTURE.md - Resource Management](ARCHITECTURE.md#resource-management) |

## Development Workflow

```
1. Review documentation:
   - README.md → Installation and usage
   - API.md → API specifications
   - ARCHITECTURE.md → System design and components

2. Make changes:
   - Follow TypeScript strict mode
   - Maintain existing code style
   - Update type definitions

3. Test changes:
   - npm run build (TypeScript compilation)
   - npm run lint (Code linting)
   - Test endpoints with cURL

4. Document changes:
   - Update README.md for user-facing changes
   - Update API.md for API changes
   - Update ARCHITECTURE.md for architectural changes
```

## Contributing

Before contributing:
1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design and components
2. Read [README.md](../README.md) for setup and configuration
3. Check [API.md](API.md) for API specifications
4. Follow TypeScript strict mode and existing code style
5. Test your changes thoroughly
6. Update relevant documentation

## Support Resources

- **Installation & Usage**: [README.md](../README.md)
- **API Reference**: [API.md](API.md)
- **System Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Bug Reports**: GitHub Issues (if available)

## Version Information

- **Current Version**: 1.0.0
- **Node.js**: 18+
- **TypeScript**: 5.3+
- **Express**: 4.18+

## License

MIT License - See project root for details

---

**Last Updated**: 2026-01-08
**Maintained by**: GeminiBridge Project
