# Troubleshooting Guide

Common issues and solutions for GeminiBridge v2.0.0

## Table of Contents

- [Installation Issues](#installation-issues)
- [CLI Execution Errors](#cli-execution-errors)
- [Authentication Failures](#authentication-failures)
- [Performance Issues](#performance-issues)
- [Docker Issues](#docker-issues)
- [Network and CORS Issues](#network-and-cors-issues)
- [Logging and Debugging](#logging-and-debugging)

## Installation Issues

### Python Version Mismatch

**Problem:** `ImportError` or syntax errors when starting the server

**Solution:**
```bash
# Check Python version (must be 3.12+)
python --version

# If using wrong version, create venv with correct Python
python3.12 -m venv .venv
```

### Dependency Installation Fails

**Problem:** `pip install -r requirements.txt` fails

**Solution:**
```bash
# Update pip first
python -m pip install --upgrade pip

# Install with verbose output to see errors
pip install -r requirements.txt -v

# If specific package fails, try installing it separately
pip install fastapi==0.115.0
```

### Virtual Environment Issues

**Problem:** Can't activate virtual environment on Windows

**Solution:**
```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# If execution policy blocks it:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Windows CMD
.\.venv\Scripts\activate.bat
```

## CLI Execution Errors

### Gemini CLI Not Found

**Problem:** `FileNotFoundError: Gemini CLI not found`

**Solution:**
```bash
# Verify Gemini CLI is installed
gemini --version

# If not found, install it:
npm install -g @google/generative-ai-cli

# Windows: Update GEMINI_CLI_PATH in .env
GEMINI_CLI_PATH=C:\Users\YourName\AppData\Roaming\npm\gemini.cmd

# Linux/Mac: Update path
GEMINI_CLI_PATH=/usr/local/bin/gemini
```

### Docker Container Conflicts (Exit Code 125)

**Problem:** `Docker container conflict` errors in logs

**Solution:**
- GeminiBridge has automatic retry logic (default: 3 retries)
- If persists, increase retry count:
  ```bash
  CLI_MAX_RETRIES=5
  ```
- Clean up orphaned containers:
  ```bash
  docker ps -a | grep sandbox
  docker rm $(docker ps -aq -f name=sandbox)
  ```

### Timeout Errors

**Problem:** Requests timing out with 504 Gateway Timeout

**Solution:**
```bash
# Increase CLI timeout in .env
GEMINI_CLI_TIMEOUT=60

# Increase queue timeout
QUEUE_TIMEOUT=60

# Check if Docker daemon is slow
docker ps  # Should respond quickly

# Restart Docker if slow
# Windows: Docker Desktop > Restart
# Linux: sudo systemctl restart docker
```

### Permission Denied Errors

**Problem:** `PermissionError` when executing Gemini CLI

**Solution:**
```bash
# Linux/Mac: Make CLI executable
chmod +x /usr/local/bin/gemini

# Windows: Run as administrator or check file permissions
# Check if antivirus is blocking execution
```

## Authentication Failures

### Invalid Bearer Token

**Problem:** `401 Unauthorized` or `Invalid bearer token`

**Solution:**
```bash
# Generate a new secure token
python scripts/generate_token.py

# Update .env with exact token (no spaces)
BEARER_TOKEN=your-exact-token-here

# Restart the server after changing token
```

### Token Too Short (Strict Mode)

**Problem:** `Bearer token must be at least 32 characters` in strict mode

**Solution:**
```bash
# Option 1: Generate longer token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 2: Disable strict mode (not recommended for production)
SECURITY_STRICT_MODE=false
```

### Authorization Header Issues

**Problem:** Client not sending proper Authorization header

**Solution:**
```python
# Correct format
headers = {
    "Authorization": "Bearer YOUR_TOKEN_HERE",  # Note the space
    "Content-Type": "application/json"
}

# Common mistakes to avoid:
# ❌ "Authorization": "YOUR_TOKEN_HERE"  # Missing "Bearer "
# ❌ "Authorization": "bearer YOUR_TOKEN"  # Wrong capitalization (should work but use "Bearer")
```

## Performance Issues

### High Latency

**Problem:** Responses are slow

**Diagnosis:**
```bash
# Check queue statistics
curl http://localhost:11434/health

# Look for:
# - High active_requests (approaching max_concurrent)
# - Long average_wait_time_ms
```

**Solutions:**
```bash
# Increase concurrent requests
MAX_CONCURRENT_REQUESTS=10

# Check if Docker is slow
docker stats  # Monitor resource usage

# Check if Gemini API is slow (external factor)
# Review logs for CLI execution time
```

### Queue Timeouts

**Problem:** `Queue timeout` errors in logs

**Solution:**
```bash
# Increase queue timeout
QUEUE_TIMEOUT=60

# Reduce concurrent requests if system is overloaded
MAX_CONCURRENT_REQUESTS=3
```

### Memory Issues

**Problem:** High memory usage or OOM errors

**Solution:**
```bash
# Check memory usage
# Windows: Task Manager
# Linux: htop or docker stats

# Reduce concurrent requests
MAX_CONCURRENT_REQUESTS=3

# Limit request size
# Check prompt_builder.py for MAX_MESSAGE_SIZE
```

## Docker Issues

### Docker Daemon Not Running

**Problem:** `Cannot connect to Docker daemon`

**Solution:**
```bash
# Windows: Start Docker Desktop

# Linux: Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify Docker is running
docker ps
```

### Docker Socket Permission Denied

**Problem:** `Permission denied` when accessing `/var/run/docker.sock`

**Solution:**
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
# Log out and log back in

# Or run with sudo (not recommended)
sudo python main.py

# Docker Compose: Ensure volume is mounted with correct permissions
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

### Sandbox Cleanup Issues

**Problem:** Many orphaned `sandbox-*` containers

**Solution:**
```bash
# List sandbox containers
docker ps -a -f name=sandbox

# Remove all stopped sandbox containers
docker container prune -f

# Or remove specific containers
docker rm $(docker ps -aq -f name=sandbox)
```

## Network and CORS Issues

### CORS Errors in Browser

**Problem:** `CORS policy: No 'Access-Control-Allow-Origin' header`

**Solution:**
```bash
# Add your frontend origin to .env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://yourdomain.com

# For credentials (cookies, auth headers)
CORS_ALLOW_CREDENTIALS=true

# Restart server after changes
```

### Port Already in Use

**Problem:** `Address already in use` on startup

**Solution:**
```bash
# Windows: Find process using port 11434
netstat -ano | findstr :11434
taskkill /PID <PID> /F

# Linux/Mac: Find and kill process
lsof -ti:11434 | xargs kill -9

# Or change port in .env
PORT=8080
```

### Cannot Access from Network

**Problem:** Server only accessible from localhost

**Solution:**
```bash
# Change HOST to allow external connections
HOST=0.0.0.0

# ⚠️ Security Warning: Only do this behind a firewall
# Always use HTTPS in production
```

## Logging and Debugging

### No Logs Generated

**Problem:** `logs/` directory is empty

**Solution:**
```bash
# Check if logs directory exists
ls logs/

# Create if missing
mkdir logs

# Verify LOG_LEVEL in .env
LOG_LEVEL=INFO

# Enable debug mode for verbose output
DEBUG=true
LOG_LEVEL=DEBUG
```

### Viewing Real-Time Logs

```bash
# Windows PowerShell
Get-Content logs\gemini-bridge-$(Get-Date -Format yyyy-MM-dd).log -Wait

# Linux/Mac
tail -f logs/gemini-bridge-$(date +%Y-%m-%d).log

# View error logs only
tail -f logs/error-$(date +%Y-%m-%d).log
```

### Parsing JSON Logs

```bash
# Pretty-print logs (requires jq)
cat logs/gemini-bridge-*.log | jq '.'

# Filter by level
cat logs/gemini-bridge-*.log | jq 'select(.level == "ERROR")'

# Filter by request ID
cat logs/gemini-bridge-*.log | jq 'select(.extra.request_id == "your-request-id")'
```

### Enable Debug Mode

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG

# Run with debug logging
LOG_LEVEL=DEBUG python main.py
```

## Advanced Debugging

### Checking Configuration

```python
# Test configuration loading
python -c "from src.config import get_config; c=get_config(); print(c.model_dump())"
```

### Testing CLI Directly

```bash
# Test Gemini CLI manually
gemini "Hello, how are you?" --model gemini-2.5-flash

# If this fails, GeminiBridge can't work
```

### Health Check

```bash
# Basic health check
curl http://localhost:11434/health

# Expected response:
# {"status":"healthy","service":"GeminiBridge Python","version":"2.0.0",...}
```

### Testing Authentication

```bash
# Test without auth (should fail)
curl http://localhost:11434/v1/models

# Test with auth (should succeed)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:11434/v1/models
```

## Getting Help

If these solutions don't help:

1. **Check Logs:** Review `logs/error-*.log` for detailed error messages
2. **Enable Debug:** Set `DEBUG=true` and `LOG_LEVEL=DEBUG`
3. **Check System:** Verify Python 3.12+, Docker, and Gemini CLI are working
4. **GitHub Issues:** Search or create issue at [GitHub Repository](https://github.com/yourusername/GeminiBridge/issues)
5. **Provide Details:** Include OS, Python version, error messages, and relevant log excerpts

---

**Last Updated:** 2026-01-09
**Version:** 2.0.0
