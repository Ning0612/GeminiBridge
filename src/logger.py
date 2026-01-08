"""
Logging System for GeminiBridge
Provides structured JSON logging with daily rotation, automatic cleanup, and sensitive data masking
"""

import json
import logging
import random
import re
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================================
# Constants
# ============================================================================

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOG_FORMAT = "%(message)s"  # We'll use custom JSON formatting
DATE_FORMAT = "%Y-%m-%d"


# ============================================================================
# Sensitive Data Masking
# ============================================================================

def mask_token(token: str, show_chars: int = 4) -> str:
    """
    Mask bearer token, showing only first and last few characters
    
    Args:
        token: Token to mask
        show_chars: Number of characters to show at start/end
        
    Returns:
        Masked token string
    """
    if len(token) <= show_chars * 2:
        return "***"
    return f"{token[:show_chars]}***{token[-show_chars:]}"


def mask_ip(ip: str) -> str:
    """
    Mask IP address's last segment
    
    Args:
        ip: IP address string
        
    Returns:
        Masked IP address
    """
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
    return ip


def mask_content(content: str, max_length: int = 100, mask_ratio: float = 0.65) -> str:
    """
    Mask content by truncating and randomly replacing characters with asterisks
    
    Args:
        content: Content to mask
        max_length: Maximum length before truncation
        mask_ratio: Ratio of characters to mask (0.6-0.7 recommended)
        
    Returns:
        Masked content string
        
    Example:
        "今天天氣很好想吃烤肉" -> "今天**好*吃烤*"
    """
    if not content:
        return ""
    
    # Truncate if too long
    truncated = content[:max_length]
    
    # Randomly mask characters
    masked_chars = []
    for char in truncated:
        # Random chance to mask this character
        if random.random() < mask_ratio:
            masked_chars.append("*")
        else:
            masked_chars.append(char)
    
    result = "".join(masked_chars)
    
    # Add ellipsis if truncated
    if len(content) > max_length:
        result += "..."
    
    return result


def mask_sensitive_data(data: Any, mask_keys: set = None) -> Any:
    """
    Recursively mask sensitive data in nested structures
    
    Args:
        data: Data to mask (dict, list, or primitive)
        mask_keys: Set of keys to mask
        
    Returns:
        Data with sensitive information masked
    """
    if mask_keys is None:
        mask_keys = {
            "authorization", "bearer_token", "token", "password", 
            "api_key", "secret", "prompt", "content", "response"
        }
    
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Mask tokens
            if "token" in key_lower or "authorization" in key_lower:
                if isinstance(value, str):
                    masked[key] = mask_token(value)
                else:
                    masked[key] = "***"
            # Mask content (prompt/response)
            elif key_lower in {"prompt", "content", "response", "message"}:
                if isinstance(value, str):
                    masked[key] = mask_content(value)
                else:
                    masked[key] = mask_sensitive_data(value, mask_keys)
            # Mask IP
            elif "ip" in key_lower:
                if isinstance(value, str):
                    masked[key] = mask_ip(value)
                else:
                    masked[key] = value
            else:
                masked[key] = mask_sensitive_data(value, mask_keys)
        return masked
    
    elif isinstance(data, list):
        return [mask_sensitive_data(item, mask_keys) for item in data]
    
    else:
        return data


# ============================================================================
# Custom JSON Formatter
# ============================================================================

class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs JSON-structured logs
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        
        Args:
            record: Log record
            
        Returns:
            JSON-formatted log string
        """
        # Base log structure
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "extra"):
            # Mask sensitive data in extra fields
            log_data["extra"] = mask_sensitive_data(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


# ============================================================================
# Log Cleanup
# ============================================================================

def cleanup_old_logs(retention_days: int) -> None:
    """
    Remove log files older than retention_days
    
    Args:
        retention_days: Number of days to retain logs
    """
    if not LOGS_DIR.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    logger = logging.getLogger("gemini_bridge")
    
    removed_count = 0
    for log_file in LOGS_DIR.glob("*.log"):
        try:
            # Extract date from filename (format: *-YYYY-MM-DD.log)
            match = re.search(r"(\d{4}-\d{2}-\d{2})\.log$", log_file.name)
            if match:
                file_date_str = match.group(1)
                file_date = datetime.strptime(file_date_str, DATE_FORMAT)
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    removed_count += 1
                    logger.info(
                        f"Cleaned up old log file: {log_file.name}",
                        extra={"extra": {"file": log_file.name, "file_date": file_date_str}}
                    )
        except Exception as e:
            logger.warning(
                f"Failed to cleanup log file: {log_file.name}",
                extra={"extra": {"error": str(e)}}
            )
    
    if removed_count > 0:
        logger.info(
            f"Log cleanup completed: removed {removed_count} old log files",
            extra={"extra": {"removed_count": removed_count, "retention_days": retention_days}}
        )


# ============================================================================
# Logger Setup
# ============================================================================

def setup_logger(
    log_level: str = "INFO",
    retention_days: int = 7,
    enable_console: bool = True
) -> logging.Logger:
    """
    Setup application logger with JSON formatting, rotation, and cleanup
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        retention_days: Number of days to retain log files
        enable_console: Whether to also output to console
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get logger
    logger = logging.getLogger("gemini_bridge")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.propagate = False  # Don't propagate to root logger
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # JSON formatter
    json_formatter = JsonFormatter()
    
    # File handler - General logs (INFO+)
    general_log_file = LOGS_DIR / f"gemini-bridge-{datetime.now().strftime(DATE_FORMAT)}.log"
    file_handler = TimedRotatingFileHandler(
        filename=general_log_file,
        when="midnight",
        interval=1,
        backupCount=0,  # We handle cleanup manually
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(json_formatter)
    file_handler.suffix = "%Y-%m-%d.log"
    logger.addHandler(file_handler)
    
    # File handler - Error logs (ERROR+)
    error_log_file = LOGS_DIR / f"error-{datetime.now().strftime(DATE_FORMAT)}.log"
    error_handler = TimedRotatingFileHandler(
        filename=error_log_file,
        when="midnight",
        interval=1,
        backupCount=0,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    error_handler.suffix = "%Y-%m-%d.log"
    logger.addHandler(error_handler)
    
    # Console handler (optional, for development)
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        # Use simple format for console
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Cleanup old logs on startup
    cleanup_old_logs(retention_days)
    
    return logger


def get_logger(name: str = "gemini_bridge") -> logging.Logger:
    """
    Get logger instance
    
    Args:
        name: Logger name (default: gemini_bridge)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
