"""Unit tests for document indexing pipeline."""
import pytest
from unittest.mock import AsyncMock, Mock, patch

from rag.indexer import DocumentIndexer


@pytest.mark.asyncio
async def test_index_document_success():
    """Test successful document indexing."""
    mock_embedding_service = Mock()
    mock_embedding_service.generate_embeddings_batch = AsyncMock(
        return_value=[[0.1] * 1536, [0.2] * 1536]
    )

    mock_session = AsyncMock()

    with patch('rag.indexer.TxtParser') as mock_parser, \
         patch('rag.indexer.MarkdownParser'), \
         patch('rag.indexer.JsonParser'), \
         patch('rag.indexer.CsvParser'), \
         patch('rag.indexer.PdfParser'):
        mock_parser.return_value.supports_incremental.return_value = False
        mock_parser.return_value.parse.return_value = {"text": "test " * 100}

        indexer = DocumentIndexer(mock_embedding_service, mock_session)
        count = await indexer.index_document("proj1", "test.txt")

        assert count > 0
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_parse_document():
    """Test document parsing integration."""
    mock_service = Mock()
    mock_session = AsyncMock()

    with patch('rag.indexer.TxtParser') as mock_parser, \
         patch('rag.indexer.MarkdownParser'), \
         patch('rag.indexer.JsonParser'), \
         patch('rag.indexer.CsvParser'), \
         patch('rag.indexer.PdfParser'):
        mock_parser.return_value.supports_incremental.return_value = False
        mock_parser.return_value.parse.return_value = {"text": "sample text"}

        indexer = DocumentIndexer(mock_service, mock_session)
        text = await indexer._parse_document("test.txt")

        assert text == "sample text"


@pytest.mark.asyncio
async def test_batch_embedding_generation():
    """Test batch processing for embeddings."""
    mock_service = Mock()
    mock_service.generate_embeddings_batch = AsyncMock(
        return_value=[[0.1] * 1536] * 5
    )
    mock_session = AsyncMock()

    indexer = DocumentIndexer(mock_service, mock_session)
    chunks = [{"content": f"chunk{i}"} for i in range(5)]

    result = await indexer._generate_embeddings(chunks)

    assert len(result) == 5
    assert all("embedding" in chunk for chunk in result)


@pytest.mark.asyncio
async def test_index_document_incremental_batches():
    """Incremental parsing should batch embeddings and DB writes."""
    async def _fake_embed(batch):
        return [[0.1] * 1536 for _ in batch]

    mock_embedding_service = Mock()
    mock_embedding_service.generate_embeddings_batch = AsyncMock(side_effect=_fake_embed)
    mock_session = AsyncMock()

    with patch('rag.indexer.TxtParser') as mock_parser, \
         patch('rag.indexer.MarkdownParser'), \
         patch('rag.indexer.JsonParser'), \
         patch('rag.indexer.CsvParser'), \
         patch('rag.indexer.PdfParser'):
        mock_parser.return_value.supports_incremental.return_value = True
        mock_parser.return_value.iter_text_segments.return_value = iter(
            ["alpha " * 200, "beta " * 200]
        )

        indexer = DocumentIndexer(mock_embedding_service, mock_session)
        indexer.batch_size = 1
        indexer.chunk_size = 64

        count = await indexer.index_document("proj1", "test.txt")

    assert count >= 2
    assert mock_embedding_service.generate_embeddings_batch.await_count == count
    mock_session.commit.assert_awaited_once()
