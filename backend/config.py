"""
Configuration module for the Personal Finance Manager.
Handles environment variables, database paths, and security settings.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Arthsutra - AI Personal Finance Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_PATH: str = str(Path(__file__).parent.parent / "data" / "finance.db")
    DATABASE_ENCRYPTION_KEY: str = Field(
        default="change_this_to_a_secure_key_in_production",
        description="Encryption key for SQLCipher database"
    )

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # AI / LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # ML Models
    CATEGORIZATION_MODEL_PATH: str = str(Path(__file__).parent / "models" / "categorization.pkl")
    FORECASTING_MODEL_PATH: str = str(Path(__file__).parent / "models" / "forecasting.pkl")

    # Security
    SECRET_KEY: str = Field(
        default="change_this_to_a_secure_random_string",
        description="Secret key for JWT tokens and encryption"
    )
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    ENCRYPTION_KEY_SIZE: int = 32

    # Data Ingestion
    ALLOWED_FILE_TYPES: list[str] = [".csv", ".pdf", ".json"]
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = str(Path(__file__).parent / "logs" / "app.log")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        Path(__file__).parent.parent / "data",
        Path(__file__).parent / "models",
        Path(__file__).parent / "logs",
        Path(__file__).parent / "ingestion",
        Path(__file__).parent / "analytics",
        Path(__file__).parent / "ai",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize directories on import
ensure_directories()