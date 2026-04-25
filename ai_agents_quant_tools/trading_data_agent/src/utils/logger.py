"""
Centralized logging configuration for the Trading Data Agent pipeline.

Usage:
    # In main.py (once at startup)
    from src.utils.logger import setup_logger
    setup_logger()

    # In any agent or tool
    from src.utils.logger import get_agent_logger
    logger = get_agent_logger("IngestionAgent")
    logger.info("Loaded 10,000 rows")
"""

from __future__ import annotations
import sys
from pathlib import Path
from loguru import logger


# ── Format strings ──────────────────────────────────────────────
CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{extra[agent]:<18}</cyan> | "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level:<8} | "
    "{extra[agent]:<18} | "
    "{module}:{function}:{line} | "
    "{message}"
)


def setup_logger(log_level: str = "DEBUG", log_dir: str = "logs") -> None:
    """
    Configure loguru with console + rotating file sinks.

    Call once at application startup before any agent runs.

    :Param: log_level: Minimum level for console output (file always captures DEBUG).
    :Param log_dir: Directory for log files. Created if it doesn't exist.
    """
    logger.remove()
    logger.configure(extra={"agent": "system"})

    Path(log_dir).mkdir(exist_ok=True)

    # Console sink — colorized, respects log_level
    logger.add(
        sink=sys.stderr,
        format=CONSOLE_FORMAT,
        level=log_level,
        colorize=True,
    )

    # File sink — always DEBUG, rotated
    logger.add(
        sink=f"{log_dir}/trading_agent_{{time}}.log",
        format=FILE_FORMAT,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
    )

    logger.info("Logger initialised")


def get_agent_logger(agent_name: str):
    """
    Return a logger instance bound to a specific agent name.

    :Param: agent_name: Identifier that appears in every log line from this agent.

    :Returns: A loguru logger with the agent name pre-bound.
    """
    return logger.bind(agent=agent_name)