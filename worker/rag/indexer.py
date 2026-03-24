"""Document indexing pipeline."""
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, text
try:
    from db_models import DocumentChunk
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from worker.db_models import DocumentChunk
from .embeddings import EmbeddingService
from .parsers import TxtParser, MarkdownParser, PdfParser
from shared.rag.indexing_core import DocumentIndexingCore


class DocumentIndexer(DocumentIndexingCore):
    """Service for indexing documents into vector database."""

    def __init__(self, embedding_service: EmbeddingService, db_session: AsyncSession):
        parsers = {
            ".txt": TxtParser(),
            ".md": MarkdownParser(),
            ".markdown": MarkdownParser(),
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
            chunks_with_embeddings = await self.prepare_document_chunks(file_path)

            # Store chunks
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

    async def _chunk_document(self, text: str, use_semantic: bool = True) -> List[Dict]:
        """Chunk document text with optional semantic mode."""
        return await self.chunk_document(text, use_semantic=use_semantic)

    async def _generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for chunks."""
        return await self.generate_embeddings(chunks)

    async def _store_chunks(
        self,
        *,
        project_id,
        rag_collection_id,
        file_path: str,
        chunks: List[Dict],
    ) -> None:
        """Store chunks in database."""
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

        payloads = self.build_chunk_payloads(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            file_path=file_path,
            chunks=chunks,
        )

        for payload in payloads:
            db_chunk = DocumentChunk(**payload)
            self.db_session.add(db_chunk)

        await self.db_session.flush()
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
        else:
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
