# Security Guide

Comprehensive security documentation for GeminiBridge v2.0.0

## Table of Contents

- [Security Overview](#security-overview)
- [Threat Model](#threat-model)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Input Validation](#input-validation)
- [Sandboxed Execution](#sandboxed-execution)
- [Data Protection](#data-protection)
- [Network Security](#network-security)
- [Logging Security](#logging-security)
- [Security Best Practices](#security-best-practices)
- [Security Checklist](#security-checklist)
- [Incident Response](#incident-response)
- [Compliance](#compliance)

## Security Overview

GeminiBridge implements a defense-in-depth security strategy with multiple layers of protection:

```
┌─────────────────────────────────────────────┐
│         Layer 1: Network Security           │
│  - HTTPS/TLS                                │
│  - Firewall Rules                           │
│  - CORS Protection                          │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│      Layer 2: Authentication                │
│  - Bearer Token Validation                  │
│  - Timing-Safe Comparison                   │
│  - Strict Mode Enforcement                  │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│       Layer 3: Rate Limiting                │
│  - Per-IP Sliding Window                    │
│  - Configurable Limits                      │
│  - DoS Protection                           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│       Layer 4: Input Validation             │
│  - Request Size Limits                      │
│  - Message Structure Validation             │
│  - Content Sanitization                     │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│     Layer 5: Execution Isolation            │
│  - Docker Sandbox                           │
│  - Temporary Workdir                        │
│  - Process Isolation                        │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│      Layer 6: Data Protection               │
│  - Sensitive Data Masking                   │
│  - Error Sanitization                       │
│  - Secure Logging                           │
└─────────────────────────────────────────────┘
```

## Threat Model

### Threat Actors

1. **Unauthenticated Attackers**
   - Attempt: Bypass authentication
   - Mitigation: Bearer token requirement, timing-safe comparison

2. **Authenticated Malicious Users**
   - Attempt: DoS attacks, resource exhaustion
   - Mitigation: Rate limiting, request size limits, queue timeouts

3. **Internal Threats**
   - Attempt: Token theft, configuration exposure
   - Mitigation: Secure file permissions, environment isolation, logging

4. **Network Attackers**
   - Attempt: Man-in-the-middle, eavesdropping
   - Mitigation: HTTPS/TLS, secure headers, CORS

### Attack Vectors

| Attack Vector | Risk Level | Mitigation |
|---------------|------------|------------|
| Brute force authentication | High | Rate limiting, strong tokens |
| DoS via large requests | High | Request size limits, timeouts |
| DoS via concurrent requests | High | Queue manager, concurrency limits |
| Timing attacks on auth | Medium | Timing-safe token comparison |
| Information disclosure via errors | Medium | Error sanitization, masking |
| Container escape | Low | Docker sandboxing, minimal permissions |
| Log injection | Low | JSON structured logging, sanitization |

## Authentication

### Bearer Token System

GeminiBridge uses Bearer token authentication for all API endpoints (except `/health`).

#### Token Generation

**Generate a cryptographically secure token:**

```bash
python scripts/generate_token.py
```

This generates a URL-safe token using `secrets.token_urlsafe(32)`, which provides 256 bits of entropy.

**Manual generation:**

```python
import secrets
token = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
```

#### Token Requirements

- Minimum: 1 character (strongly discouraged)
- **Recommended**: 32+ characters for production use
- Use cryptographically secure random tokens
- Generate using `python scripts/generate_token.py`

#### Token Storage

**DO:**
- Store in `.env` file with restrictive permissions (chmod 600)
- Use environment variables
- Keep separate tokens for dev/staging/production

**DON'T:**
- Commit to version control
- Include in code or configuration files
- Share via email or chat
- Reuse across different environments

#### Token Validation

Implementation uses timing-safe comparison to prevent timing attacks:

```python
# Timing-safe comparison
max_len = max(len(provided), len(expected))
provided_padded = provided.ljust(max_len)
expected_padded = expected.ljust(max_len)

if not hmac.compare_digest(provided_padded, expected_padded):
    return 401  # Invalid token
```

**Why timing-safe?**

Regular string comparison (`==`) may leak information about token correctness through execution time differences, enabling timing attacks.

### Authentication Flow

```
1. Client sends request with Authorization header
   Authorization: Bearer abc123...

2. Middleware extracts token
   auth_header = request.headers.get("authorization")
   parts = auth_header.split()
   provided_token = parts[1]

3. Timing-safe comparison
   if hmac.compare_digest(provided_token, expected_token):
       ✓ Allow request
   else:
       ✗ Return 401 Unauthorized

4. Request proceeds or error returned
```

### Authentication Errors

| Error Code | HTTP Status | Cause |
|------------|-------------|-------|
| `missing_auth_header` | 401 | No Authorization header |
| `invalid_auth_header` | 401 | Invalid header format |
| `invalid_token` | 401 | Token mismatch |

## Rate Limiting

### Implementation

Per-IP sliding window rate limiting prevents abuse and DoS attacks.

#### Algorithm

```python
def check_rate_limit(ip: str):
    current_time = time.time()

    # Remove expired requests
    requests[ip] = [
        ts for ts in requests[ip]
        if current_time - ts < window_seconds
    ]

    # Check limit
    if len(requests[ip]) >= max_requests:
        return False  # Rate limit exceeded

    # Record current request
    requests[ip].append(current_time)
    return True  # Allow request
```

#### Default Configuration

```bash
RATE_LIMIT_MAX_REQUESTS=100  # Requests per window
RATE_LIMIT_WINDOW_SECONDS=60  # Window size (1 minute)
```

#### Production Recommendations

**Low-traffic API:**
```bash
RATE_LIMIT_MAX_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
```

**High-traffic API:**
```bash
RATE_LIMIT_MAX_REQUESTS=500
RATE_LIMIT_WINDOW_SECONDS=300  # 5 minutes
```

**Enterprise API:**
```bash
# Implement per-user rate limiting
# Use Redis-based distributed rate limiter
```

### Rate Limit Headers

Response includes remaining quota:

```http
HTTP/1.1 200 OK
X-RateLimit-Remaining: 95
```

### Rate Limit Error

When exceeded:

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

### Bypassing Rate Limits

**Valid reasons:**
- Internal services (trusted IPs)
- Health check monitoring
- Load testing (use separate environment)

**Implementation:**
```python
# Add to rate_limit_middleware
BYPASS_IPS = ["127.0.0.1", "10.0.0.0/8"]

if client_ip in BYPASS_IPS:
    return await call_next(request)  # Skip rate limiting
```

## Input Validation

### Request Validation

Multiple layers of validation prevent malicious input:

#### 1. Message Structure Validation

```python
# Required fields
valid_roles = {"system", "user", "assistant"}

for msg in messages:
    if "role" not in msg or "content" not in msg:
        return 400  # Missing required fields

    if msg["role"] not in valid_roles:
        return 400  # Invalid role
```

#### 2. Request Size Limits

```python
# DoS protection
if len(messages) > 100:
    return 400  # Too many messages

if len(message["content"]) > 100000:
    return 400  # Message too long
```

**Limits:**
- **Max messages:** 100 per request
- **Max content:** 100,000 characters per message
- **Max history:** 20 messages used (truncated)

#### 3. Model Name Validation

```python
# Map to known models or use fallback
if model in model_mappings:
    gemini_model = model_mappings[model]
else:
    gemini_model = "gemini-2.5-flash"  # Safe fallback
```

### Input Sanitization

**Error messages sanitized before returning:**

```python
def sanitize_error_message(text: str) -> str:
    # Remove Windows paths
    text = re.sub(r'[A-Za-z]:\\[\w\\]+', '[PATH]', text)

    # Remove Unix paths
    text = re.sub(r'/[\w/]+/[\w/]+', '[PATH]', text)

    # Remove container IDs
    text = re.sub(r'container.*?[a-f0-9-]{12,}', 'container [ID]', text)

    # Remove IP addresses
    text = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP]', text)

    return text
```

## Sandboxed Execution

### Docker Sandbox

All Gemini CLI executions run in Docker containers for isolation.

#### Sandbox Configuration

```python
# Always enabled
CLI_USE_SANDBOX = True

# CLI arguments
args = [gemini_cli_path, "-m", model, "--sandbox"]
```

#### Isolation Features

1. **Process Isolation**
   - Each request runs in separate container
   - Automatic cleanup on completion

2. **Filesystem Isolation**
   - Temporary workdir per request
   - No access to host filesystem (except Docker socket)

3. **Network Isolation**
   - Container network restrictions
   - Only outbound to Gemini API

#### Sandbox Security

**Permissions:**
```bash
# Docker socket (read-only recommended)
-v /var/run/docker.sock:/var/run/docker.sock:ro
```

**Container Cleanup:**
```python
# Automatic cleanup on conflict
if docker_conflict_detected(result):
    subprocess.run(['docker', 'rm', '-f', container_name])
```

### Workdir Isolation

Each request uses isolated temporary directory:

```python
def _create_temp_workdir(request_id: str) -> Path:
    temp_dir = Path(tempfile.gettempdir()) / f"gemini-bridge-{request_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
```

**Cleanup:**
```python
finally:
    shutil.rmtree(workdir)  # Always cleanup
```

## Data Protection

### Sensitive Data Masking

Automatic masking in logs and error messages:

#### Token Masking

```python
def mask_token(token: str, show_chars: int = 4) -> str:
    if len(token) <= show_chars * 2:
        return "***"
    return f"{token[:show_chars]}***{token[-show_chars:]}"

# Example:
"abc123xyz789" → "abc1***xyz9"
```

#### IP Address Masking

```python
def mask_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
    return ip

# Example:
"192.168.1.100" → "192.168.1.***"
```

#### Content Masking

```python
def mask_content(content: str, mask_ratio: float = 0.65) -> str:
    masked_chars = []
    for char in content:
        if random.random() < mask_ratio:
            masked_chars.append("*")
        else:
            masked_chars.append(char)
    return "".join(masked_chars)

# Example:
"Hello world" → "He**o *or**"
```

### PII Protection

**Automatically masked in logs:**
- Bearer tokens (only first/last 4 chars shown)
- IP addresses (last segment masked)
- Request prompts (65% masked)
- Response content (65% masked)
- File paths (replaced with [PATH])
- Container IDs (replaced with [ID])

### Data Retention

**Logs:**
- Default retention: 7 days
- Production recommendation: 30 days
- Automatic cleanup on startup
- Manual cleanup: `cleanup_old_logs(retention_days)`

**No persistent storage:**
- No request history saved
- No user data stored
- Stateless architecture

## Network Security

### HTTPS/TLS

**Always use HTTPS in production:**

```nginx
# nginx configuration
server {
    listen 443 ssl http2;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
}
```

### Security Headers

**Recommended headers:**

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### CORS Configuration

**Current Implementation**: CORS settings are hardcoded in `src/app.py`.

**Default Configuration**:
```python
allow_origins=[
    "http://localhost:*",
    "http://127.0.0.1:*",
    "chrome-extension://*",
    "moz-extension://*"
]
allow_credentials=True
```

**To customize CORS**: Modify the `CORSMiddleware` configuration in `src/app.py`.

**Production Recommendations**:
- Limit origins to specific domains (no wildcards)
- Example: `["https://yourdomain.com", "https://app.yourdomain.com"]`
- Use HTTPS only in production

### Firewall Rules

```bash
# Allow HTTPS only
sudo ufw allow 443/tcp

# Block direct application access
sudo ufw deny 11434/tcp

# Allow SSH for management
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

## Logging Security

### Structured Logging

JSON format prevents log injection:

```json
{
    "timestamp": "2024-01-09T12:00:00.123456",
    "level": "INFO",
    "message": "Request completed",
    "extra": {
        "request_id": "abc-123",
        "masked_data": "***"
    }
}
```

### Log File Permissions

```bash
# Restrict log access
chmod 600 /opt/geminibridge/logs/*.log
chown geminibridge:geminibridge /opt/geminibridge/logs
```

### Log Rotation

**Daily rotation with retention:**

```python
file_handler = TimedRotatingFileHandler(
    filename=log_file,
    when="midnight",
    interval=1,
    backupCount=0,  # Manual cleanup
    encoding="utf-8"
)
```

### What NOT to Log

**Never log:**
- Raw bearer tokens
- Complete user prompts
- Complete model responses
- User IP addresses (unmasked)
- File system paths
- Container IDs

**Always mask:**
- Tokens (show first/last 4 chars)
- IPs (mask last segment)
- Content (65% random masking)

## Security Best Practices

### Development

1. **Never commit secrets**
   ```bash
   # .gitignore
   .env
   .env.local
   .env.production
   ```

2. **Use separate tokens per environment**
   ```bash
   # Development
   BEARER_TOKEN=dev-token-123

   # Production
   BEARER_TOKEN=prod-secure-token-456
   ```

3. **Run security checks**
   ```bash
   python scripts/check_security.py
   pip-audit  # Check dependencies
   ```

### Deployment

1. **Use strong tokens (32+ chars)**
   ```bash
   python scripts/generate_token.py
   ```

2. **Restrict file permissions**
   ```bash
   chmod 600 .env
   chmod 600 logs/*.log
   ```

3. **Enable HTTPS/TLS**
   ```bash
   # Use Let's Encrypt or similar
   certbot --nginx -d api.yourdomain.com
   ```

4. **Configure firewall**
   ```bash
   sudo ufw enable
   sudo ufw allow 443/tcp
   sudo ufw deny 11434/tcp
   ```

5. **Customize CORS in src/app.py** - Limit to specific production domains

### Monitoring

1. **Monitor authentication failures**
   ```bash
   grep "invalid_token" logs/error-*.log
   ```

2. **Monitor rate limit events**
   ```bash
   grep "rate_limit_exceeded" logs/gemini-bridge-*.log
   ```

3. **Monitor Docker conflicts**
   ```bash
   grep "Docker container conflict" logs/error-*.log
   ```

4. **Set up alerts**
   ```bash
   # Alert on high error rate
   # Alert on authentication failures
   # Alert on rate limit exceeded
   ```

### Incident Response

1. **Rotate compromised tokens immediately**
   ```bash
   # Generate new token
   python scripts/generate_token.py

   # Update .env
   # Restart service
   sudo systemctl restart geminibridge
   ```

2. **Review logs for unauthorized access**
   ```bash
   grep "401" logs/gemini-bridge-*.log
   grep "429" logs/gemini-bridge-*.log
   ```

3. **Block malicious IPs**
   ```bash
   # Via firewall
   sudo ufw deny from <IP_ADDRESS>

   # Via nginx
   deny <IP_ADDRESS>;
   ```

## Security Checklist

### Pre-Deployment

- [ ] Generate strong bearer token (32+ characters)
- [ ] Configure appropriate CORS origins in `src/app.py`
- [ ] Set restrictive file permissions (chmod 600 .env)
- [ ] Review and adjust rate limits
- [ ] Run `python scripts/check_security.py`
- [ ] Run `pip-audit` to check dependencies
- [ ] Configure HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Configure security headers in reverse proxy

### Post-Deployment

- [ ] Verify HTTPS/TLS is working
- [ ] Test authentication with invalid token
- [ ] Test rate limiting with multiple requests
- [ ] Verify logs are being written with masking
- [ ] Test error sanitization
- [ ] Monitor authentication failures
- [ ] Set up security alerts
- [ ] Document incident response procedures

### Periodic Reviews

- [ ] Rotate bearer tokens (quarterly)
- [ ] Review and update rate limits
- [ ] Audit access logs for anomalies
- [ ] Update dependencies (`pip install -U`)
- [ ] Run security scans (`pip-audit`)
- [ ] Review firewall rules
- [ ] Update SSL/TLS certificates
- [ ] Review and archive old logs

## Incident Response

### Suspected Token Compromise

1. **Immediate Actions**
   ```bash
   # Generate new token
   python scripts/generate_token.py

   # Update .env
   nano .env

   # Restart service
   sudo systemctl restart geminibridge
   ```

2. **Investigation**
   ```bash
   # Review authentication logs
   grep "invalid_token" logs/error-*.log

   # Check for unauthorized access
   grep "200" logs/gemini-bridge-*.log | grep -v "expected-ip"
   ```

3. **Notification**
   - Notify security team
   - Document incident
   - Review access logs

### DoS Attack

1. **Immediate Actions**
   ```bash
   # Reduce rate limits
   RATE_LIMIT_MAX_REQUESTS=10
   RATE_LIMIT_WINDOW_SECONDS=60

   # Restart service
   sudo systemctl restart geminibridge
   ```

2. **Block Attacker**
   ```bash
   # Identify attacking IPs
   grep "429" logs/gemini-bridge-*.log | cut -d'"' -f4 | sort | uniq -c | sort -nr

   # Block via firewall
   sudo ufw deny from <ATTACKER_IP>
   ```

3. **Recovery**
   - Monitor queue statistics
   - Gradually increase limits
   - Implement additional rate limiting (e.g., distributed)

### Data Breach

1. **Containment**
   ```bash
   # Stop service immediately
   sudo systemctl stop geminibridge
   ```

2. **Assessment**
   - Review all logs
   - Identify compromised data
   - Determine breach scope

3. **Remediation**
   - Rotate all tokens
   - Update security measures
   - Notify affected parties (if applicable)
   - Document lessons learned

## Compliance

### GDPR Considerations

**Data minimization:**
- No persistent user data storage
- Automatic log masking
- Configurable retention periods

**Right to erasure:**
- Logs automatically deleted after retention period
- No user profiles or history

**Data protection:**
- Encryption in transit (HTTPS/TLS)
- Access controls (authentication)
- Audit logging

### SOC 2 Considerations

**Access controls:**
- Bearer token authentication
- Rate limiting
- IP-based restrictions

**Logging and monitoring:**
- Structured JSON logging
- Audit trail via request IDs
- Security event monitoring

**Incident response:**
- Documented procedures
- Security checklist
- Regular security reviews

### Security Audit

**Regular reviews:**
1. Dependency scanning (`pip-audit`)
2. Configuration review (`check_security.py`)
3. Log analysis (authentication failures, rate limits)
4. Access review (who has tokens?)
5. Infrastructure review (firewall, TLS, etc.)

---

For security issues or questions:
- Review [Architecture Guide](ARCHITECTURE.md) for technical details
- Check [Deployment Guide](DEPLOYMENT.md) for secure deployment
- Submit security issues privately via email (not public issues)
