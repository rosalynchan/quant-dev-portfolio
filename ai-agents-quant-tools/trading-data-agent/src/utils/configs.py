"""
Configuration management for the Trading Data Agent pipeline.

Loads settings from environment variables and .env file using
Pydantic BaseSettings. All configuration is accessed through
get_settings() which returns a cached singleton.

Usage:
    from src.utils.config import get_settings

    settings = get_settings()
    print(settings.LOG_LEVEL)
"""

from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    """
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive = True,)
      
    OPENAI_API_KEY: str ="not-set"
    LOG_LEVEL: str =  "DEBUG"
    LOG_DIR: str="logs"
    MAX_ITERATIONS: int =10
    DEFAULT_DATA_DIR: str="data"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    First call reads .env and creates the object.
    Subsequent calls return the same instance.

    """
    return Settings()