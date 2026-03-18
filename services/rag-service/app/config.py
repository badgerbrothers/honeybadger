"""Configuration management."""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Development defaults - DO NOT use in production
    database_url: str = "postgresql://badgers:badgers_dev_password@localhost:5432/badgers"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "admin"
    rabbitmq_password: str = "password"

    # OpenAI API
    openai_api_key: str = ""

    # RAG Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Object storage configuration.
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

    @property
    def rabbitmq_url(self) -> str:
        """Build AMQP connection URL from RabbitMQ settings."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )


settings = Settings()
