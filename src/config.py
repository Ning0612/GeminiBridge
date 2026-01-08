"""
Configuration loader for GeminiBridge Python
Loads environment variables and model mappings with validation
"""

import json
import os
from pathlib import Path
from typing import Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Note: Cannot import logger here to avoid circular dependency
# Logger will be initialized in main.py before config is used extensively


class AppConfig(BaseSettings):
    """Application configuration with validation"""

    # Server
    port: int = Field(default=11434, ge=1, le=65535)
    host: str = Field(default="127.0.0.1")

    # Security (REQUIRED)
    bearer_token: str = Field(min_length=1)

    # Gemini CLI
    gemini_cli_timeout: int = Field(default=30, ge=1, le=300)  # 1-300 seconds

    # Rate Limiting
    rate_limit_max_requests: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    # Concurrency Control
    max_concurrent_requests: int = Field(default=5, ge=1, le=50)
    queue_timeout: int = Field(default=30, ge=1, le=300)

    # Logging
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)
    log_retention_days: int = Field(default=7, ge=1)

    # Retry Logic (for Docker sandbox conflicts)
    cli_max_retries: int = Field(default=3, ge=0, le=10)

    # Gemini CLI Path Configuration
    # Default to 'gemini' (assumes in PATH), but can be overridden with full path
    gemini_cli_path: str = Field(default="gemini")

    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("bearer_token")
    @classmethod
    def validate_bearer_token(cls, v: str) -> str:
        """Validate bearer token strength"""
        if len(v) < 32:
            print("⚠️  WARNING: BEARER_TOKEN should be at least 32 characters for security")
        if v == "your-secret-token-here-change-this-in-production":
            print("⚠️  WARNING: Please change the default BEARER_TOKEN in production")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper


def load_model_mappings(config_dir: Path = None) -> Dict[str, str]:
    """
    Load model mappings from JSON file
    Returns default mappings if file not found or invalid
    """
    if config_dir is None:
        # Look for config directory relative to this file
        config_dir = Path(__file__).parent.parent / "config"

    models_path = config_dir / "models.json"

    default_mappings = {
        "gpt-3.5-turbo": "gemini-2.5-flash",
        "gpt-4": "gemini-2.5-pro",
    }

    try:
        if not models_path.exists():
            print(f"⚠️  Model mappings file not found: {models_path}")
            print("Using default mappings")
            return default_mappings

        with open(models_path, "r", encoding="utf-8") as f:
            mappings = json.load(f)

        if not isinstance(mappings, dict):
            print("⚠️  Invalid model mappings format (must be dict)")
            return default_mappings

        print(f"✅ Loaded {len(mappings)} model mappings from {models_path}")
        return mappings

    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse model mappings JSON: {e}")
        return default_mappings
    except Exception as e:
        print(f"⚠️  Failed to load model mappings: {e}")
        return default_mappings


# Singleton config instance
_config: AppConfig | None = None
_model_mappings: Dict[str, str] | None = None


def get_config() -> AppConfig:
    """Get singleton config instance"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def get_model_mappings() -> Dict[str, str]:
    """Get singleton model mappings"""
    global _model_mappings
    if _model_mappings is None:
        _model_mappings = load_model_mappings()
    return _model_mappings


def get_default_model() -> str:
    """Get default fallback model"""
    return "gemini-2.5-flash"


# Sandbox configuration - always enabled for security
CLI_USE_SANDBOX = True  # Always use --sandbox flag
