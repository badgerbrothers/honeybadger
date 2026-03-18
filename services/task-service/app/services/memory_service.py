"""Memory service for conversation summarization and project knowledge management."""
from typing import List
import json
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import structlog
from app.models.memory import ProjectMemory
from app.models.conversation import Message
from app.config import settings

logger = structlog.get_logger()


class MemoryService:
    """Service for memory operations using OpenAI."""

    def __init__(self, api_key: str = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.embedding_model = "text-embedding-3-small"

    async def summarize_conversation(self, messages: List[Message]) -> str:
        """Generate a concise summary of conversation messages."""
        if not messages:
            return "Empty conversation"

        conversation_text = "\n".join([
            f"{msg.role.value}: {msg.content}" for msg in messages
        ])

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize the following conversation concisely, highlighting key topics, decisions, and action items."},
                    {"role": "user", "content": conversation_text}
                ],
                max_tokens=500
            )
            content = response.choices[0].message.content
            return content if content else "Unable to generate summary"
        except Exception as e:
            logger.error("OpenAI summarization failed", error=str(e))
            raise Exception("AI service unavailable")

    async def extract_memory_facts(
        self, conversation_id: uuid.UUID, db: AsyncSession
    ) -> List[dict]:
        """Extract key facts from conversation and generate embeddings."""
        result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        messages = result.scalars().all()

        if not messages:
            return []

        conversation_text = "\n".join([f"{msg.role.value}: {msg.content}" for msg in messages])

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract 3-5 key facts, preferences, or decisions from this conversation. Return as a JSON array of strings."},
                    {"role": "user", "content": conversation_text}
                ],
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            if not content:
                return []

            facts_data = json.loads(content)
            facts = facts_data.get("facts", [])

            embeddings = await self._generate_embeddings(facts)

            return [
                {"content": fact, "embedding": emb}
                for fact, emb in zip(facts, embeddings)
            ]
        except Exception as e:
            logger.error("Memory extraction failed", error=str(e))
            raise Exception("AI service unavailable")

    async def search_memories(
        self, project_id: uuid.UUID, query: str, limit: int, db: AsyncSession
    ) -> List[ProjectMemory]:
        """Search project memories using semantic similarity."""
        query_embedding = await self._generate_embedding(query)

        result = await db.execute(
            select(ProjectMemory)
            .where(ProjectMemory.project_id == project_id)
            .order_by(ProjectMemory.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        return result.scalars().all()

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (public method)."""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model, input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise Exception("AI service unavailable")

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = await self.client.embeddings.create(
            model=self.embedding_model, input=text
        )
        return response.data[0].embedding

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []
        response = await self.client.embeddings.create(
            model=self.embedding_model, input=texts
        )
        return [item.embedding for item in response.data]


memory_service = MemoryService()
