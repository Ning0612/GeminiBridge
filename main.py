"""
GeminiBridge - OpenAI API-compatible proxy for Gemini CLI
Main entry point for the application
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    import uvicorn
    from src.app import app
    from src.config import get_config
    from src.logger import setup_logger, get_logger

    # Load configuration
    config = get_config()

    # Setup logging system
    logger = setup_logger(
        log_level=config.log_level,
        retention_days=config.log_retention_days,
        enable_console=True
    )

    # Log startup information
    logger.info(
        "GeminiBridge Python - Starting Server",
        extra={"extra": {
            "host": config.host,
            "port": config.port,
            "max_concurrent_requests": config.max_concurrent_requests,
            "log_level": config.log_level,
            "log_retention_days": config.log_retention_days
        }}
    )

    # Start the server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
    )

