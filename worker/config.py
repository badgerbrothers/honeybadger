"""Worker configuration management."""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from models.types import ProviderType


class Settings(BaseSettings):
    """Worker settings."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://badgers:badgers_dev_password@localhost:5432/badgers"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "admin"
    rabbitmq_password: str = "password"

    # Model settings
    model_provider: ProviderType = ProviderType.OPENAI
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    anthropic_api_key: str | None = None
    default_model: str = "gpt-4"
    default_main_model: str = "gpt-5.3-codex"
    default_openai_model: str = "gpt-4-turbo"
    default_anthropic_model: str = "claude-3-opus-20240229"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    temperature: float = 0.7
    max_tokens: int = 2000

    # Object storage
    s3_endpoint: str = Field(
        default="localhost:9000",
        validation_alias=AliasChoices("S3_ENDPOINT", "MINIO_ENDPOINT"),
    )
    s3_access_key: str = Field(
        default="badgers",
        validation_alias=AliasChoices("S3_ACCESS_KEY", "MINIO_ACCESS_KEY"),
    )
    s3_secret_key: str = Field(
        default="badgers_dev_password",
        validation_alias=AliasChoices("S3_SECRET_KEY", "MINIO_SECRET_KEY"),
    )
    s3_bucket: str = Field(
        default="badgers-artifacts",
        validation_alias=AliasChoices("S3_BUCKET", "MINIO_BUCKET"),
    )
    s3_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices("S3_SECURE", "MINIO_SECURE"),
    )

    # Worker settings
    worker_mode: str = "polling"
    worker_poll_interval: int = 5  # seconds
    backend_base_url: str = "http://localhost:8002"
    internal_service_token: str = "dev-internal-token"
    sandbox_image: str = "badgers-sandbox:latest"
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_quota: int = 50000

    @property
    def rabbitmq_url(self) -> str:
        """Build AMQP connection URL from RabbitMQ settings."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )


settings = Settings()
