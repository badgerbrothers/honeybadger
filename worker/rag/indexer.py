"""Document indexing pipeline."""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from db_models import DocumentChunk
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from worker.db_models import DocumentChunk
from .embeddings import EmbeddingService
from .parsers import CsvParser, JsonParser, MarkdownParser, PdfParser, TxtParser
from shared.rag.indexing_core import DocumentIndexingCore


class DocumentIndexer(DocumentIndexingCore):
    """Service for indexing documents into vector database."""

    def __init__(self, embedding_service: EmbeddingService, db_session: AsyncSession):
        parsers = {
            ".txt": TxtParser(),
            ".md": MarkdownParser(),
            ".markdown": MarkdownParser(),
            ".json": JsonParser(),
            ".csv": CsvParser(),
            ".pdf": PdfParser(),
        }
        super().__init__(embedding_service=embedding_service, parsers=parsers)
        self.db_session = db_session

    async def index_document(
        self,
        project_id,
        file_path: str,
        rag_collection_id=None,
    ) -> int:
        """Index a document into vector database.

        Returns:
            Number of chunks created
        """
        try:
            if self.supports_incremental_processing(file_path):
                return await self._index_document_incrementally(
                    project_id=project_id,
                    rag_collection_id=rag_collection_id,
                    file_path=file_path,
                )

            chunks_with_embeddings = await self.prepare_document_chunks(file_path)

            await self._store_chunks(
                project_id=project_id,
                rag_collection_id=rag_collection_id,
                file_path=file_path,
                chunks=chunks_with_embeddings,
            )

            return len(chunks_with_embeddings)
        except Exception:
            await self.db_session.rollback()
            raise

    async def _parse_document(self, file_path: str) -> str:
        """Parse document to extract text."""
        return await self.parse_document(file_path)

    async def _chunk_document(self, text: str, use_semantic: bool = True) -> list[dict[str, Any]]:
        """Chunk document text with optional semantic mode."""
        return await self.chunk_document(text, use_semantic=use_semantic)

    async def _generate_embeddings(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate embeddings for chunks."""
        return await self.generate_embeddings(chunks)

    async def _index_document_incrementally(
        self,
        *,
        project_id,
        rag_collection_id,
        file_path: str,
    ) -> int:
        """Index large text-like documents without materializing all chunks in memory."""
        await self._delete_existing_chunks(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            file_path=file_path,
        )

        total_chunks = 0
        async for chunk_batch in self.iter_document_chunk_batches(
            file_path,
            use_semantic=False,
            batch_size=self.batch_size,
        ):
            embedded_batch = await self.generate_embeddings(chunk_batch)
            await self._add_chunk_batch(
                project_id=project_id,
                rag_collection_id=rag_collection_id,
                file_path=file_path,
                chunks=embedded_batch,
            )
            total_chunks += len(embedded_batch)

        await self._refresh_text_search_vector(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            file_path=file_path,
        )
        await self.db_session.commit()
        return total_chunks

    async def _delete_existing_chunks(
        self,
        *,
        project_id,
        rag_collection_id,
        file_path: str,
    ) -> None:
        """Delete prior chunks for the same scope and file."""
        if rag_collection_id is not None:
            scope_filter = DocumentChunk.rag_collection_id == rag_collection_id
        else:
            scope_filter = DocumentChunk.project_id == project_id

        await self.db_session.execute(
            delete(DocumentChunk).where(
                scope_filter,
                DocumentChunk.file_path == file_path,
            )
        )

    async def _add_chunk_batch(
        self,
        *,
        project_id,
        rag_collection_id,
        file_path: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        """Insert one hydrated chunk batch."""
        if not chunks:
            return

        payloads = self.build_chunk_payloads(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            file_path=file_path,
            chunks=chunks,
        )
        await self.db_session.execute(insert(DocumentChunk), payloads)

    async def _refresh_text_search_vector(
        self,
        *,
        project_id,
        rag_collection_id,
        file_path: str,
    ) -> None:
        """Refresh PostgreSQL full-text search vectors for the indexed file."""
        if rag_collection_id is not None:
            await self.db_session.execute(
                text(
                    """
                    UPDATE document_chunk
                    SET text_search_vector = to_tsvector('english', content)
                    WHERE rag_collection_id = :rag_collection_id
                      AND file_path = :file_path
                    """
                ),
                {"rag_collection_id": str(rag_collection_id), "file_path": file_path},
            )
            return

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

    async def _store_chunks(
        self,
        *,
        project_id,
        rag_collection_id,
        file_path: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        """Store chunks in database."""
        await self._delete_existing_chunks(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            file_path=file_path,
        )
        await self._add_chunk_batch(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            file_path=file_path,
            chunks=chunks,
        )
        await self._refresh_text_search_vector(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            file_path=file_path,
        )
        await self.db_session.commit()
