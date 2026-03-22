"""HTTP client for rag-service operations."""
from __future__ import annotations

import uuid

import httpx

from app.config import settings


class RagClient:
    """Client for scheduling document indexing in rag-service."""

    def __init__(self) -> None:
        self.base_url = settings.rag_service_url.rstrip("/")

    async def schedule_indexing(
        self,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        authorization_header: str | None = None,
    ) -> dict:
        headers: dict[str, str] = {}
        if authorization_header:
            headers["Authorization"] = authorization_header
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/api/rag/projects/{project_id}/documents/index",
                json={"node_id": str(node_id)},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_rag_collection(
        self,
        rag_collection_id: uuid.UUID,
        authorization_header: str | None = None,
    ) -> dict:
        headers: dict[str, str] = {}
        if authorization_header:
            headers["Authorization"] = authorization_header
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.base_url}/api/rags/{rag_collection_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()


rag_client = RagClient()
