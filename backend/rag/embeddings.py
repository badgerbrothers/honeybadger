"""Embedding generation service using OpenAI API."""
from typing import List
from openai import AsyncOpenAI


class EmbeddingService:
    """Service for generating embeddings using OpenAI API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if len(texts) > 2048:
            raise ValueError("Batch size cannot exceed 2048")

        response = await self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]
