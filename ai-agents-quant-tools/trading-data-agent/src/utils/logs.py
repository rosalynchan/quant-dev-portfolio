"""
Logger configuration for the Trading Data Multi-Agent Assistant.
"""

from loguru import logger
import sys
from pathlib import Path


def setup_logger(name: str = "TradingDataAssistant"):
    """
    Configure and return a logger instance.
    
    :param name: Name for the logger
    
    :returns: A configured loguru logger instance
    
    Example:
        logger = setup_logger("IngestionAgent")
        logger.info("Starting data ingestion")
    """
    logger.remove()
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Add console output (stderr)
    logger.add(
        sink=sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
        level="DEBUG"
    )
    
    # Add file output
    logger.add(
        sink=str(logs_dir / "app.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )
    
    return logger


# Create default logger instance
logger = setup_logger()
logger = setup_logger("Test")
logger.info("Hello world")