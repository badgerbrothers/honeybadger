"""Configuration management."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Development defaults - DO NOT use in production
    database_url: str = "postgresql://manus:manus_dev_password@localhost:5432/manus"
    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()
