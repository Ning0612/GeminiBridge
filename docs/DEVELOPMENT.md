# Development Guide

Comprehensive development workflow and guidelines for GeminiBridge v2.0.0

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Debugging](#debugging)
- [Contributing](#contributing)
- [Release Process](#release-process)

## Development Setup

### Prerequisites

**Required:**
- Python 3.12 or higher
- Docker (for sandboxed CLI execution)
- Git
- Gemini CLI installed

**Optional:**
- Visual Studio Code (recommended IDE)
- Python extensions for VS Code

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/GeminiBridge.git
   cd GeminiBridge
   ```

2. **Create virtual environment**
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

4. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

   **requirements-dev.txt:**
   ```
   # Testing
   pytest==8.0.0
   pytest-asyncio==0.23.0
   pytest-cov==4.1.0
   httpx==0.26.0

   # Code Quality
   black==24.0.0
   ruff==0.1.0
   mypy==1.8.0

   # Security
   pip-audit==2.6.0

   # Documentation
   mkdocs==1.5.0
   mkdocs-material==9.5.0
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env

   # Generate token for development
   python scripts/generate_token.py

   # Edit .env with your settings
   # Windows: notepad .env
   # Linux/Mac: nano .env
   ```

6. **Verify setup**
   ```bash
   # Check Python version
   python --version

   # Check Docker
   docker --version

   # Check Gemini CLI
   gemini --version

   # Run security check
   python scripts/check_security.py
   ```

### VS Code Setup

**.vscode/settings.json:**
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.rulers": [88],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

**.vscode/launch.json:**
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Main",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env"
        },
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

## Project Structure

```
GeminiBridge/
├── main.py                 # Application entry point
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── .env.example           # Environment configuration template
├── .gitignore             # Git ignore rules
├── README.md              # Project overview
├── CLAUDE.md              # AI assistant guidance
├── LICENSE                # Project license
│
├── config/
│   └── models.json        # Model mapping configuration
│
├── src/                   # Source code
│   ├── __init__.py
│   ├── app.py             # FastAPI application
│   ├── config.py          # Configuration loader
│   ├── gemini_cli.py      # Gemini CLI adapter
│   ├── queue_manager.py   # Concurrency control
│   ├── logger.py          # Logging system
│   └── prompt_builder.py  # Prompt formatter
│
├── scripts/               # Utility scripts
│   ├── generate_token.py  # Token generator
│   └── check_security.py  # Security checker
│
├── docs/                  # Documentation
│   ├── API.md             # API reference
│   ├── ARCHITECTURE.md    # Architecture guide
│   ├── DEPLOYMENT.md      # Deployment guide
│   ├── SECURITY.md        # Security documentation
│   └── DEVELOPMENT.md     # This file
│
├── tests/                 # Test files
│   ├── __init__.py
│   ├── test_app.py
│   ├── test_config.py
│   ├── test_gemini_cli.py
│   ├── test_queue_manager.py
│   ├── test_logger.py
│   └── test_prompt_builder.py
│
└── logs/                  # Generated log files
    ├── gemini-bridge-YYYY-MM-DD.log
    └── error-YYYY-MM-DD.log
```

## Development Workflow

### Git Workflow

**Branch Strategy:**
```
main
 ├── develop
 │    ├── feature/feature-name
 │    ├── bugfix/bug-name
 │    └── hotfix/critical-fix
 └── release/vX.Y.Z
```

**Branch Naming:**
- `feature/add-streaming-support`
- `bugfix/fix-rate-limiting`
- `hotfix/fix-authentication`
- `release/v2.1.0`

### Development Cycle

1. **Create feature branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   ```bash
   # Edit code
   # Add tests
   # Update documentation
   ```

3. **Test changes**
   ```bash
   # Run tests
   pytest

   # Check code quality
   black src/
   ruff check src/
   mypy src/

   # Security check
   python scripts/check_security.py
   pip-audit
   ```

4. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: add streaming support for chat completions"
   ```

   **Commit Message Format:**
   ```
   <type>(<scope>): <subject>

   <body>

   <footer>
   ```

   **Types:**
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation
   - `style`: Formatting
   - `refactor`: Code refactoring
   - `test`: Adding tests
   - `chore`: Maintenance

   **Example:**
   ```
   feat(api): add streaming support for chat completions

   - Implement SSE streaming response
   - Add streaming parameter validation
   - Update API documentation

   Closes #123
   ```

5. **Push changes**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create pull request**
   - Go to GitHub
   - Create PR from feature branch to develop
   - Fill in PR template
   - Request review

### Running the Development Server

**Standard mode:**
```bash
python main.py
```

**With auto-reload (using uvicorn directly):**
```bash
# Windows:
.\.venv\Scripts\uvicorn.exe src.app:app --reload --host 127.0.0.1 --port 11434

# Linux/Mac:
.venv/bin/uvicorn src.app:app --reload --host 127.0.0.1 --port 11434
```

**With debug logging:**
```bash
LOG_LEVEL=DEBUG python main.py
```

**With custom configuration:**
```bash
PORT=8080 HOST=0.0.0.0 python main.py
```

## Code Style

### Python Style Guide

Follow **PEP 8** with some modifications:

- **Line length:** 88 characters (Black default)
- **Indentation:** 4 spaces
- **Quotes:** Double quotes for strings
- **Imports:** Grouped and sorted

### Code Formatting

**Use Black for automatic formatting:**
```bash
# Format all files
black src/

# Check without modifying
black --check src/

# Format specific file
black src/app.py
```

### Linting

**Use Ruff for linting:**
```bash
# Check all files
ruff check src/

# Auto-fix issues
ruff check --fix src/

# Check specific file
ruff check src/app.py
```

### Type Checking

**Use mypy for type checking:**
```bash
# Check all files
mypy src/

# Check specific file
mypy src/app.py

# With strict mode
mypy --strict src/
```

### Import Organization

**Order:**
1. Standard library imports
2. Third-party imports
3. Local imports

**Example:**
```python
# Standard library
import os
import time
from pathlib import Path

# Third-party
from fastapi import FastAPI, Request
from pydantic import BaseModel

# Local
from .config import get_config
from .logger import get_logger
```

### Docstrings

**Use Google-style docstrings:**

```python
def execute_gemini_cli(prompt: str, model: str, request_id: str) -> CLIExecutionResult:
    """
    Execute Gemini CLI in synchronous mode with automatic retry on Docker conflicts.

    This function is blocking and should be called from a thread pool.

    Args:
        prompt: Formatted prompt string
        model: Gemini model name (e.g., "gemini-2.5-pro")
        request_id: Unique request identifier for logging

    Returns:
        CLIExecutionResult with execution outcome

    Raises:
        subprocess.TimeoutExpired: If execution exceeds timeout
        subprocess.SubprocessError: If subprocess execution fails

    Example:
        >>> result = execute_gemini_cli("Hello", "gemini-2.5-flash", "req-123")
        >>> if result.success:
        ...     print(result.content)
    """
    pass
```

## Testing

### Test Structure

**Create tests in `tests/` directory:**

```python
# tests/test_app.py
import pytest
from fastapi.testclient import TestClient

from src.app import app

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Create authentication headers"""
    return {"Authorization": "Bearer test-token"}

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_models_requires_auth(client):
    """Test models endpoint requires authentication"""
    response = client.get("/v1/models")
    assert response.status_code == 401

def test_list_models_with_auth(client, auth_headers):
    """Test models endpoint with authentication"""
    response = client.get("/v1/models", headers=auth_headers)
    assert response.status_code == 200
    assert "data" in response.json()
```

### Running Tests

**Run all tests:**
```bash
pytest
```

**Run specific test file:**
```bash
pytest tests/test_app.py
```

**Run specific test:**
```bash
pytest tests/test_app.py::test_health_check
```

**Run with coverage:**
```bash
pytest --cov=src --cov-report=html
```

**Run with verbose output:**
```bash
pytest -v
```

**Run with debug output:**
```bash
pytest -s
```

### Test Coverage

**Minimum coverage requirement: 80%**

**Generate coverage report:**
```bash
pytest --cov=src --cov-report=html

# View in browser:
# Windows:
start htmlcov\index.html
# Linux/Mac:
open htmlcov/index.html
```

**Coverage by module:**
```bash
pytest --cov=src --cov-report=term-missing
```

## Debugging

### Debug Logging

**Enable debug logging:**
```bash
# Via environment variable
DEBUG=true python main.py

# Via .env file
echo "LOG_LEVEL=DEBUG" >> .env
python main.py
```

**Add debug logging in code:**
```python
from src.logger import get_logger

logger = get_logger("gemini_bridge")

logger.debug(
    "Debug information",
    extra={"extra": {
        "variable": value,
        "details": data
    }}
)
```

### VS Code Debugging

**Set breakpoints in VS Code:**
1. Click left margin to set breakpoint
2. Press F5 to start debugging
3. Use debug toolbar to step through code

**Debug configuration (already in `.vscode/launch.json`):**
- "Python: Main" - Debug main.py
- "Python: Current File" - Debug current file

### Interactive Debugging

**Use pdb for interactive debugging:**
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

**Common pdb commands:**
- `n` - Next line
- `s` - Step into
- `c` - Continue
- `l` - List code
- `p variable` - Print variable
- `q` - Quit

### Request Debugging

**Test endpoints with curl:**
```bash
# Health check
curl http://localhost:11434/health

# List models (with auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:11434/v1/models

# Chat completion
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Test with Python:**
```python
import requests

# Health check
response = requests.get("http://localhost:11434/health")
print(response.json())

# Chat completion
response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
print(response.json())
```

### Log Analysis

**View real-time logs:**
```bash
# General logs
tail -f logs/gemini-bridge-$(date +%Y-%m-%d).log

# Error logs
tail -f logs/error-$(date +%Y-%m-%d).log

# Filtered logs
tail -f logs/gemini-bridge-*.log | grep "request_id"
```

**Parse JSON logs:**
```bash
# Pretty-print logs
cat logs/gemini-bridge-*.log | jq '.'

# Filter by level
cat logs/gemini-bridge-*.log | jq 'select(.level == "ERROR")'

# Extract specific fields
cat logs/gemini-bridge-*.log | jq '{timestamp, level, message}'
```

## Contributing

### Code Review Checklist

**Before submitting PR:**

- [ ] Code follows style guide (Black, Ruff)
- [ ] All tests pass (`pytest`)
- [ ] Code coverage maintained (>80%)
- [ ] Type hints added (`mypy`)
- [ ] Documentation updated
- [ ] Security check passes
- [ ] Commit messages follow convention
- [ ] No sensitive data in code

**PR Description Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Security considerations addressed
```

### Review Process

1. **Automated Checks**
   - CI runs tests
   - Code quality checks
   - Security scanning

2. **Peer Review**
   - At least 1 approval required
   - Address feedback
   - Update code as needed

3. **Merge**
   - Squash and merge to develop
   - Delete feature branch

## Release Process

### Versioning

**Semantic Versioning (SemVer):**
- **Major (X.0.0):** Breaking changes
- **Minor (x.Y.0):** New features (backwards compatible)
- **Patch (x.y.Z):** Bug fixes

### Release Steps

1. **Create release branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/v2.1.0
   ```

2. **Update version**
   ```python
   # src/__init__.py
   __version__ = "2.1.0"
   ```

3. **Update changelog**
   ```markdown
   # CHANGELOG.md
   ## [2.1.0] - 2024-01-15

   ### Added
   - Streaming support for chat completions
   - New rate limiting configuration options

   ### Fixed
   - Docker container cleanup issue
   - Authentication timing attack vulnerability
   ```

4. **Run tests and checks**
   ```bash
   pytest
   black --check src/
   ruff check src/
   mypy src/
   python scripts/check_security.py
   ```

5. **Commit and push**
   ```bash
   git add .
   git commit -m "chore: prepare release v2.1.0"
   git push origin release/v2.1.0
   ```

6. **Create PR to main**
   - Review all changes
   - Get approvals
   - Merge to main

7. **Tag release**
   ```bash
   git checkout main
   git pull origin main
   git tag -a v2.1.0 -m "Release version 2.1.0"
   git push origin v2.1.0
   ```

8. **Merge back to develop**
   ```bash
   git checkout develop
   git merge main
   git push origin develop
   ```

9. **Create GitHub release**
   - Go to GitHub Releases
   - Create new release from tag
   - Add changelog
   - Upload artifacts (if any)

### Hotfix Process

For critical production bugs:

1. **Create hotfix branch from main**
   ```bash
   git checkout main
   git checkout -b hotfix/fix-critical-bug
   ```

2. **Fix bug and test**
   ```bash
   # Make changes
   # Add tests
   pytest
   ```

3. **Update version (patch)**
   ```python
   __version__ = "2.0.1"
   ```

4. **Merge to main and develop**
   ```bash
   # To main
   git checkout main
   git merge hotfix/fix-critical-bug
   git tag v2.0.1

   # To develop
   git checkout develop
   git merge hotfix/fix-critical-bug

   # Push
   git push origin main develop --tags
   ```

---

For additional help:
- [API Documentation](API.md)
- [Architecture Guide](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Security Guide](SECURITY.md)
