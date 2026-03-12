"""Document indexing pipeline."""
from pathlib import Path
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from .embeddings import EmbeddingService
from .chunker import chunk_text
from .parsers import TxtParser, MarkdownParser, PdfParser


class DocumentIndexer:
    """Service for indexing documents into vector database."""

    def __init__(self, embedding_service: EmbeddingService, db_session: AsyncSession):
        self.embedding_service = embedding_service
        self.db_session = db_session
        self.parsers = {
            ".txt": TxtParser(),
            ".md": MarkdownParser(),
            ".markdown": MarkdownParser(),
            ".pdf": PdfParser(),
        }

    async def index_document(
        self, project_id: str, file_path: str, content: str = None
    ) -> int:
        """Index a document into vector database."""
        text = await self._parse_document(file_path, content)
        chunks = await self._chunk_document(text)
        chunks_with_embeddings = await self._generate_embeddings(chunks)
        await self._store_chunks(project_id, file_path, chunks_with_embeddings)
        return len(chunks)

    async def _parse_document(self, file_path: str, content: str = None) -> str:
        """Parse document to extract text."""
        ext = Path(file_path).suffix.lower()
        parser = self.parsers.get(ext)

        if not parser:
            raise ValueError(f"Unsupported file type: {ext}")

        result = parser.parse(Path(file_path))
        return result["text"]

    async def _chunk_document(self, text: str) -> List[Dict]:
        """Chunk document text."""
        return chunk_text(text, chunk_size=512, overlap=50)

    async def _generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for chunks."""
        texts = [chunk["content"] for chunk in chunks]

        all_embeddings = []
        batch_size = 2048

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.embedding_service.generate_embeddings_batch(batch)
            all_embeddings.extend(embeddings)

        for chunk, embedding in zip(chunks, all_embeddings):
            chunk["embedding"] = embedding

        return chunks

    async def _store_chunks(
        self, project_id: str, file_path: str, chunks: List[Dict]
    ) -> None:
        """Store chunks in database."""
        from app.models.document_chunk import DocumentChunk

        for chunk in chunks:
            db_chunk = DocumentChunk(
                project_id=project_id,
                file_path=file_path,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                embedding=chunk["embedding"],
                token_count=chunk["token_count"],
                chunk_metadata={"start_pos": chunk["start_pos"], "end_pos": chunk["end_pos"]}
            )
            self.db_session.add(db_chunk)

        await self.db_session.commit()
