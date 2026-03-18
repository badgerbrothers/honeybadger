"""Document indexing pipeline."""
from pathlib import Path
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, text
from .embeddings import EmbeddingService
from .chunker import chunk_text
from .semantic_chunker import SemanticChunker
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
        self, project_id, file_path: str
    ) -> int:
        """Index a document into vector database.

        Returns:
            Number of chunks created
        """
        try:
            # Parse document
            text = await self._parse_document(file_path)

            # Chunk document
            chunks = await self._chunk_document(text)

            # Generate embeddings
            chunks_with_embeddings = await self._generate_embeddings(chunks)

            # Store chunks
            await self._store_chunks(project_id, file_path, chunks_with_embeddings)

            return len(chunks)
        except Exception:
            await self.db_session.rollback()
            raise

    async def _parse_document(self, file_path: str) -> str:
        """Parse document to extract text."""
        ext = Path(file_path).suffix.lower()
        parser = self.parsers.get(ext)

        if not parser:
            raise ValueError(f"Unsupported file type: {ext}")

        result = parser.parse(Path(file_path))
        return result["text"]

    async def _chunk_document(self, text: str, use_semantic: bool = True) -> List[Dict]:
        """Chunk document text with optional semantic mode."""
        if use_semantic:
            semantic_chunker = SemanticChunker(max_chunk_size=512, overlap=50)
            return semantic_chunker.chunk_text(text)
        return chunk_text(text, chunk_size=512, overlap=50)

    async def _generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for chunks."""
        texts = [chunk["content"] for chunk in chunks]

        # Batch process (max 2048 per batch)
        all_embeddings = []
        batch_size = 2048

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.embedding_service.generate_embeddings_batch(batch)
            all_embeddings.extend(embeddings)

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, all_embeddings):
            chunk["embedding"] = embedding

        return chunks

    async def _store_chunks(
        self, project_id: str, file_path: str, chunks: List[Dict]
    ) -> None:
        """Store chunks in database."""
        from backend.app.models.document_chunk import DocumentChunk

        await self.db_session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.project_id == project_id,
                DocumentChunk.file_path == file_path,
            )
        )

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

        await self.db_session.flush()
        await self.db_session.execute(
            text(
                """
                UPDATE document_chunk
                SET text_search_vector = to_tsvector('english', content)
                WHERE project_id = :project_id
                  AND file_path = :file_path
                """
            ),
            {"project_id": str(project_id), "file_path": file_path},
        )
        await self.db_session.commit()
