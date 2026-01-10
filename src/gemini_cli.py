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
import random
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


def _wait_for_container_to_stop(container_name: str, timeout_seconds: int = 30) -> bool:
    """
    Wait for a container to stop naturally (polling every 1 second)
    
    Args:
        container_name: Name of the container to wait for
        timeout_seconds: Maximum time to wait in seconds
        
    Returns:
        True if container stopped within timeout, False otherwise
    """
    import time
    
    start_time = time.time()
    poll_interval = 1.0  # Check every 1 second
    
    logger.info(
        "Waiting for container to complete naturally",
        extra={"extra": {"container_name": container_name, "timeout_seconds": timeout_seconds}}
    )
    
    while (time.time() - start_time) < timeout_seconds:
        try:
            # Check if container still exists and is running
            result = subprocess.run(
                ['docker', 'inspect', '--format', '{{.State.Running}}', container_name],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode != 0:
                # Container doesn't exist anymore
                logger.info(
                    "Container no longer exists",
                    extra={"extra": {"container_name": container_name}}
                )
                return True
            
            is_running = result.stdout.strip().lower() == 'true'
            
            if not is_running:
                # Container stopped
                elapsed = time.time() - start_time
                logger.info(
                    "Container stopped naturally",
                    extra={"extra": {"container_name": container_name, "waited_seconds": round(elapsed, 2)}}
                )
                return True
            
            # Still running, wait before next check
            time.sleep(poll_interval)
            
        except subprocess.TimeoutExpired:
            logger.warning(
                "Timeout checking container status",
                extra={"extra": {"container_name": container_name}}
            )
            return False
        except Exception as e:
            logger.warning(
                "Error checking container status",
                extra={"extra": {"container_name": container_name, "error": str(e)}}
            )
            return False
    
    # Timeout reached
    elapsed = time.time() - start_time
    logger.warning(
        "Container still running after timeout",
        extra={"extra": {"container_name": container_name, "waited_seconds": round(elapsed, 2)}}
    )
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


def _cleanup_docker_container(container_name: str, force_stop: bool = False) -> bool:
    """
    Attempt to remove Docker container by name
    By default, only removes stopped containers to avoid interfering with running requests
    
    Args:
        container_name: Name of the container to remove
        force_stop: If True, forcefully stop and remove; if False, only remove if already stopped
        
    Returns:
        True if successful, False otherwise
    """
    config = get_config()
    timeout = config.docker_cleanup_timeout
    
    try:
        if force_stop:
            # Force stop - only use this when we know it's a conflict
            stop_result = subprocess.run(
                ['docker', 'stop', container_name],
                capture_output=True,
                timeout=timeout,
                text=True
            )
        
        # Try to remove (will fail if container is still running without force_stop)
        result = subprocess.run(
            ['docker', 'rm', '-f' if force_stop else '', container_name],
            capture_output=True,
            timeout=timeout,
            text=True
        )

        if result.returncode == 0:
            logger.debug(
                "Docker container cleanup successful",
                extra={"extra": {"container_name": container_name, "forced": force_stop}}
            )
            return True
        else:
            # It's OK if removal fails for running containers when not forcing
            if not force_stop and "is not stopped" in result.stderr.lower():
                logger.debug(
                    "Skipped cleanup of running container",
                    extra={"extra": {"container_name": container_name}}
                )
                return False
            
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


def _get_running_containers() -> list[str]:
    """
    Get list of running sandbox containers
    Returns list of container names for diagnostics
    """
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '-f', 'name=sandbox', '--format', '{{.Names}}'],
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            containers = [c.strip() for c in result.stdout.strip().split('\n') if c.strip()]
            return containers
        return []
    except Exception as e:
        logger.debug(
            "Failed to get running containers",
            extra={"extra": {"error": str(e)}}
        )
        return []


def _cleanup_all_sandbox_containers() -> tuple[int, int]:
    """
    Proactively cleanup stopped sandbox containers before execution
    Only removes containers that are already stopped to avoid interfering with running requests
    Returns tuple of (total_found, successfully_cleaned)
    """
    config = get_config()
    
    if not config.enable_proactive_cleanup:
        return (0, 0)
    
    try:
        # Get all sandbox containers (including stopped ones)
        containers = _get_running_containers()
        
        if not containers:
            return (0, 0)
        
        logger.debug(
            "Proactive cleanup: checking sandbox containers",
            extra={"extra": {"count": len(containers), "containers": containers}}
        )
        
        success_count = 0
        failed_containers = []
        
        for container in containers:
            # Only remove stopped containers (force_stop=False)
            # This prevents interfering with containers from concurrent requests
            cleanup_result = _cleanup_docker_container(container, force_stop=False)
            if cleanup_result:
                success_count += 1
            else:
                # Track failed cleanups for debugging
                failed_containers.append(container)
        
        if success_count > 0:
            logger.info(
                "Proactive cleanup: removed stopped containers",
                extra={"extra": {
                    "total_checked": len(containers),
                    "cleaned": success_count,
                    "failed": len(failed_containers)
                }}
            )
        
        if failed_containers:
            logger.debug(
                "Proactive cleanup: some containers still running",
                extra={"extra": {"running_containers": failed_containers}}
            )
        
        return (len(containers), success_count)
        
    except Exception as e:
        logger.warning(
            "Error during proactive cleanup",
            extra={"extra": {"error": str(e)}}
        )
        return (0, 0)


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
    else:
        config = get_config()
    
    # Proactive cleanup before first execution attempt
    cleanup_wait_ms = config.cli_cleanup_wait_ms / 1000  # Convert to seconds
    if config.enable_proactive_cleanup:
        total, cleaned = _cleanup_all_sandbox_containers()
        if total > 0:
            logger.info(
                "Proactive cleanup before execution",
                extra={"extra": {"request_id": request_id, "containers_found": total, "cleaned": cleaned}}
            )
            # Wait a bit after cleanup
            time.sleep(cleanup_wait_ms)

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

                # Strategy: Wait for container to complete naturally first
                # Only force-stop if it's still running after timeout
                config = get_config()
                wait_timeout = config.gemini_cli_timeout  # Use CLI timeout as wait time
                
                container_stopped = _wait_for_container_to_stop(container_name, wait_timeout)
                
                if container_stopped:
                    # Container stopped naturally, try to remove it
                    cleanup_success = _cleanup_docker_container(container_name, force_stop=False)
                else:
                    # Container still running after timeout, force cleanup
                    logger.warning(
                        "Container did not stop naturally, forcing cleanup",
                        extra={"extra": {"container_name": container_name}}
                    )
                    cleanup_success = _cleanup_docker_container(container_name, force_stop=True)

                if cleanup_success:
                    logger.info(
                        "Retrying after Docker cleanup",
                        extra={"extra": {"attempt": attempt + 1, "max_retries": max_retries}}
                    )
                    # Smart random delay based on attempt number to reduce retry conflicts
                    # Attempt 0 (first retry): 100-300ms
                    # Attempt 1 (second retry): 200-500ms
                    # Attempt 2+ (third+ retry): 300-800ms
                    if attempt == 0:
                        random_delay = random.uniform(0.1, 0.3)
                    elif attempt == 1:
                        random_delay = random.uniform(0.2, 0.5)
                    else:
                        random_delay = random.uniform(0.3, 0.8)
                    
                    total_delay = cleanup_wait_ms + random_delay
                    logger.debug(
                        "Applying smart delay before retry",
                        extra={"extra": {
                            "attempt": attempt,
                            "cleanup_wait_s": cleanup_wait_ms,
                            "random_delay_s": round(random_delay, 3),
                            "total_delay_s": round(total_delay, 3)
                        }}
                    )
                    time.sleep(total_delay)
                    continue  # Retry
                else:
                    logger.warning("Cleanup failed, retrying anyway")
                    # Apply smart delay even on cleanup failure
                    if attempt == 0:
                        random_delay = random.uniform(0.1, 0.3)
                    elif attempt == 1:
                        random_delay = random.uniform(0.2, 0.5)
                    else:
                        random_delay = random.uniform(0.3, 0.8)
                    time.sleep(cleanup_wait_ms + random_delay)
                    continue  # Retry even if cleanup failed
            else:
                # Couldn't extract container name, but still retry
                if attempt < max_retries:
                    logger.warning("Docker conflict detected but couldn't extract container name, retrying")
                    # Apply smart delay
                    if attempt == 0:
                        random_delay = random.uniform(0.1, 0.3)
                    elif attempt == 1:
                        random_delay = random.uniform(0.2, 0.5)
                    else:
                        random_delay = random.uniform(0.3, 0.8)
                    time.sleep(cleanup_wait_ms + random_delay)
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
