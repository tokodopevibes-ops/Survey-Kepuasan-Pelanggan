"""
Configuration settings for the Kuesioner application.
Loads settings from environment variables using Pydantic Settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database Configuration
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "kuesioner"
    db_user: str = "root"
    db_password: str = ""

    # JWT Configuration
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # App Configuration
    app_name: str = "Kuesioner"
    app_version: str = "1.0.0"
    debug: bool = True

    @property
    def database_url(self) -> str:
        """Construct MySQL database URL."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    @property
    def async_database_url(self) -> str:
        """Construct async MySQL database URL (for future use)."""
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
