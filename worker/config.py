"""Worker configuration management."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from models.types import ProviderType

class Settings(BaseSettings):
    """Worker settings."""
    model_config = SettingsConfigDict(env_file=".env")

    model_provider: ProviderType = ProviderType.OPENAI
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    default_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000

settings = Settings()
