"""Configuration management."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Development defaults - DO NOT use in production
    database_url: str = "postgresql://badgers:badgers@localhost:5432/badgers"
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI API
    openai_api_key: str = ""

    # RAG Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    chunk_size: int = 512
    chunk_overlap: int = 50

    class Config:
        env_file = ".env"

settings = Settings()
