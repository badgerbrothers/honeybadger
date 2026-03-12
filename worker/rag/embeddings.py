"""Embedding generation service using OpenAI API."""
from openai import AsyncOpenAI, RateLimitError, APIError
from typing import List
import asyncio


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return (await self.generate_embeddings_batch([text]))[0]

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (max 2048)."""
        if len(texts) > 2048:
            raise ValueError("Batch size cannot exceed 2048")

        for attempt in range(3):
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                return [item.embedding for item in response.data]
            except RateLimitError:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
            except APIError as e:
                if attempt < 2 and e.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
