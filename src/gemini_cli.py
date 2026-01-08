"""
Gemini CLI Adapter
Executes Gemini CLI via subprocess with platform-specific handling
Includes automatic retry on Docker sandbox container conflicts
"""

import os
import platform
import subprocess
import tempfile
import shutil
import re
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

from .config import CLI_USE_SANDBOX, get_config
from .logger import get_logger


# ============================================================================
# Logger
# ============================================================================

logger = get_logger("gemini_bridge")


@dataclass
class CLIExecutionResult:
    """Result of CLI execution"""
    success: bool
    content: str | None = None
    error: str | None = None
    exit_code: int = 0
    stderr: str = ""
    execution_time_ms: int = 0


def _is_windows() -> bool:
    """Check if running on Windows"""
    return platform.system() == "Windows"


def _create_temp_workdir(request_id: str) -> Path:
    """
    Create temporary working directory for CLI execution
    Isolated directory per request for security

    Args:
        request_id: Unique request identifier

    Returns:
        Path to temporary directory
    """
    temp_dir = Path(tempfile.gettempdir()) / f"gemini-bridge-{request_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _cleanup_temp_workdir(workdir: Path, request_id: str) -> None:
    """
    Cleanup temporary working directory

    Args:
        workdir: Path to temporary directory
        request_id: Request identifier for logging
    """
    try:
        if workdir.exists():
            shutil.rmtree(workdir)
    except Exception as e:
        # Non-critical error, just log warning
        logger.warning(
            "Failed to cleanup temp directory",
            extra={"extra": {"request_id": request_id, "error": str(e)}}
        )


def _mask_sensitive(content: str, max_length: int = 50) -> str:
    """Mask sensitive information in logs"""
    if len(content) <= max_length:
        return "[MASKED]"
    return content[:max_length] + "...[MASKED]"


def _is_docker_conflict_error(exit_code: int, stderr: str) -> bool:
    """
    Check if error is Docker container name conflict
    Exit code 125 + stderr contains "Conflict" or "already in use"
    """
    if exit_code != 125:
        return False

    conflict_patterns = [
        r"already in use",
        r"Conflict",
        r"container name.*is already in use"
    ]

    for pattern in conflict_patterns:
        if re.search(pattern, stderr, re.IGNORECASE):
            return True

    return False


def _extract_container_name(stderr: str) -> str | None:
    """
    Extract container name from Docker error message
    Example: The container name "/sandbox-0.23.0-0" is already in use
    """
    match = re.search(r'container name ["\']?([^"\']+)["\']? is already in use', stderr, re.IGNORECASE)
    if match:
        container_name = match.group(1)
        # Remove leading slash if present
        return container_name.lstrip('/')
    return None


def _cleanup_docker_container(container_name: str) -> bool:
    """
    Attempt to remove Docker container by name
    Returns True if successful, False otherwise
    """
    try:
        # Try to remove container (force remove even if running)
        result = subprocess.run(
            ['docker', 'rm', '-f', container_name],
            capture_output=True,
            timeout=5,
            text=True
        )

        if result.returncode == 0:
            logger.debug(
                "Docker container cleanup successful",
                extra={"extra": {"container_name": container_name}}
            )
            return True
        else:
            logger.warning(
                "Failed to cleanup Docker container",
                extra={"extra": {"container_name": container_name, "stderr": result.stderr.strip()}}
            )
            return False

    except subprocess.TimeoutExpired:
        logger.warning(
            "Timeout cleaning up Docker container",
            extra={"extra": {"container_name": container_name}}
        )
        return False
    except Exception as e:
        logger.warning(
            "Error cleaning up Docker container",
            extra={"extra": {"container_name": container_name, "error": str(e)}}
        )
        return False


def execute_gemini_cli_sync(
    prompt: str,
    model: str,
    request_id: str,
    max_retries: int | None = None
) -> CLIExecutionResult:
    """
    Execute Gemini CLI in synchronous mode with automatic retry on Docker conflicts
    This function is blocking and should be called from a thread pool

    IMPORTANT Windows Behavior:
    - On Windows, CLI MUST be executed through shell for correct behavior
    - Using shell=False or full paths can cause incorrect response content
    - This matches Node.js implementation requirements

    Retry Logic:
    - Automatically retries on Docker container name conflicts (exit code 125)
    - Attempts to cleanup conflicting container before retry
    - Max 3 retries by default

    Args:
        prompt: Formatted prompt string
        model: Gemini model name
        request_id: Unique request identifier
        max_retries: Maximum retry attempts (default: 3)

    Returns:
        CLIExecutionResult with execution outcome
    """
    import time
    start_time = time.time()

    # Get max_retries from config if not specified
    if max_retries is None:
        config = get_config()
        max_retries = config.cli_max_retries

    # Retry loop
    for attempt in range(max_retries + 1):  # 0-indexed, so +1 for total attempts
        is_retry = attempt > 0

        if is_retry:
            logger.info(
                "Retrying CLI execution",
                extra={"extra": {"request_id": request_id, "attempt": attempt, "max_retries": max_retries}}
            )

        result = _execute_gemini_cli_internal(prompt, model, request_id, start_time)

        # Check if this is a Docker conflict error
        if not result.success and _is_docker_conflict_error(result.exit_code, result.stderr):
            # Extract container name and try to cleanup
            container_name = _extract_container_name(result.stderr)

            if container_name:
                logger.warning(
                    "Docker container conflict detected",
                    extra={"extra": {"container_name": container_name, "request_id": request_id}}
                )

                # Last attempt? Don't retry anymore
                if attempt >= max_retries:
                    logger.error(
                        "Max retries reached for request",
                        extra={"extra": {"request_id": request_id, "max_retries": max_retries}}
                    )
                    break

                # Try to cleanup the conflicting container
                cleanup_success = _cleanup_docker_container(container_name)

                if cleanup_success:
                    logger.info(
                        "Retrying after Docker cleanup",
                        extra={"extra": {"attempt": attempt + 1, "max_retries": max_retries}}
                    )
                    # Wait a bit before retry
                    time.sleep(0.5)
                    continue  # Retry
                else:
                    logger.warning("Cleanup failed, retrying anyway")
                    time.sleep(0.5)
                    continue  # Retry even if cleanup failed
            else:
                # Couldn't extract container name, but still retry
                if attempt < max_retries:
                    logger.warning("Docker conflict detected but couldn't extract container name, retrying")
                    time.sleep(0.5)
                    continue
                else:
                    break
        else:
            # Success or non-retryable error
            if is_retry and result.success:
                logger.info(
                    "Request succeeded after retries",
                    extra={"extra": {"request_id": request_id, "retry_count": attempt}}
                )
            break

    return result


def _execute_gemini_cli_internal(
    prompt: str,
    model: str,
    request_id: str,
    start_time: float
) -> CLIExecutionResult:
    """
    Internal CLI execution (called by retry wrapper)
    """
    import time

    config = get_config()
    timeout = config.gemini_cli_timeout
    debug_mode = config.debug
    cli_path = config.gemini_cli_path

    # Create temp working directory
    workdir = _create_temp_workdir(request_id)

    try:
        # Build command arguments
        args = [cli_path, "-m", model]
        if CLI_USE_SANDBOX:
            args.append("--sandbox")

        if debug_mode:
            logger.debug(
                "Executing Gemini CLI",
                extra={"extra": {
                    "command": ' '.join(args),
                    "prompt_length": len(prompt),
                    "prompt_hex_preview": prompt.encode('utf-8').hex()[:100]
                }}
            )

        # Platform-specific subprocess configuration
        if _is_windows():
            # Using shell=False with full path for better security
            # CLI_PATH should point to .cmd file on Windows
            creation_flags = subprocess.CREATE_NO_WINDOW  # Prevent console popup
            result = subprocess.run(
                args,
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=int(timeout),
                cwd=str(workdir),
                shell=False,
                creationflags=creation_flags
            )
        else:
            # On Unix-like systems, shell=False is safer
            result = subprocess.run(
                args,
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=timeout,
                cwd=str(workdir),
                shell=False
            )

        execution_time_ms = int((time.time() - start_time) * 1000)


        # Decode stdout/stderr
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()

        if debug_mode:
            logger.debug(
                "CLI execution result",
                extra={"extra": {
                    "exit_code": result.returncode,
                    "stdout_length": len(stdout),
                    "stdout_preview": stdout[:200]
                }}
            )

        # Check exit code
        if result.returncode != 0:
            return CLIExecutionResult(
                success=False,
                error=f"CLI exited with code {result.returncode}",
                exit_code=result.returncode,
                stderr=stderr,
                execution_time_ms=execution_time_ms
            )

        # Check if stdout is empty
        if not stdout:
            return CLIExecutionResult(
                success=False,
                error="Empty response from CLI",
                exit_code=0,
                stderr=stderr,
                execution_time_ms=execution_time_ms
            )

        # Success
        return CLIExecutionResult(
            success=True,
            content=stdout,
            exit_code=0,
            stderr=stderr,
            execution_time_ms=execution_time_ms
        )

    except subprocess.TimeoutExpired:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return CLIExecutionResult(
            success=False,
            error="Execution timeout",
            exit_code=-1,
            stderr="Process killed due to timeout",
            execution_time_ms=execution_time_ms
        )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return CLIExecutionResult(
            success=False,
            error=str(e),
            exit_code=-1,
            stderr="",
            execution_time_ms=execution_time_ms
        )

    finally:
        # Always cleanup temp directory
        _cleanup_temp_workdir(workdir, request_id)


# Async wrapper for FastAPI (runs in thread pool)
async def execute_gemini_cli(
    prompt: str,
    model: str,
    request_id: str
) -> CLIExecutionResult:
    """
    Execute Gemini CLI (async wrapper)
    Runs synchronous subprocess in thread pool to avoid blocking event loop

    Args:
        prompt: Formatted prompt string
        model: Gemini model name
        request_id: Unique request identifier

    Returns:
        CLIExecutionResult with execution outcome
    """
    import anyio

    # Run blocking subprocess in thread pool
    # This prevents blocking FastAPI's event loop
    result = await anyio.to_thread.run_sync(
        execute_gemini_cli_sync,
        prompt,
        model,
        request_id
    )

    return result
