"""Compatibility wrapper around shared embedding utilities."""

from shared.rag import embeddings as shared_embeddings

APIError = shared_embeddings.APIError
APITimeoutError = shared_embeddings.APITimeoutError
AsyncOpenAI = shared_embeddings.AsyncOpenAI
RateLimitError = shared_embeddings.RateLimitError


class EmbeddingService(shared_embeddings.EmbeddingService):
    """Preserve the worker module patch surface while delegating logic to shared code."""

    def __init__(self, api_key: str | None, model: str = "text-embedding-3-small", dimension: int = 1536):
        original_client = shared_embeddings.AsyncOpenAI
        shared_embeddings.AsyncOpenAI = AsyncOpenAI
        try:
            super().__init__(api_key=api_key, model=model, dimension=dimension)
        finally:
            shared_embeddings.AsyncOpenAI = original_client


__all__ = [
    "APIError",
    "APITimeoutError",
    "AsyncOpenAI",
    "RateLimitError",
    "EmbeddingService",
]
