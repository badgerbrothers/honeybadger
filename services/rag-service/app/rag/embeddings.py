"""Embedding generation service for rag-service."""
from __future__ import annotations

import hashlib
import logging
import math
from typing import List

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI with local fallback."""

    def __init__(self, api_key: str | None, model: str = "text-embedding-3-small", dimension: int = 1536):
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = model
        self.dimension = dimension
        self._fallback_logged = False

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate one embedding vector."""
        return (await self.generate_embeddings_batch([text]))[0]

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of inputs."""
        if len(texts) > 2048:
            raise ValueError("Batch size cannot exceed 2048")

        if self.client is None:
            self._log_fallback_once("missing_openai_api_key")
            return [self._fallback_embedding(text) for text in texts]

        try:
            response = await self.client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            self._log_fallback_once(f"openai_error:{type(e).__name__}")
            return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str) -> List[float]:
        """Create deterministic local embedding to keep retrieval available."""
        vector = [0.0] * self.dimension
        tokens = text.lower().split()

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, len(digest), 4):
                chunk = int.from_bytes(digest[offset : offset + 4], "big")
                index = chunk % self.dimension
                sign = 1.0 if (chunk & 1) == 0 else -1.0
                vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _log_fallback_once(self, reason: str) -> None:
        if self._fallback_logged:
            return
        self._fallback_logged = True
        logger.warning(
            "embedding_fallback_enabled",
            extra={
                "reason": reason,
                "dimension": self.dimension,
                "model": self.model,
            },
        )
