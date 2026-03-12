"""Unit tests for document indexing pipeline."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from rag.indexer import DocumentIndexer


@pytest.mark.asyncio
async def test_index_document_success():
    """Test successful document indexing."""
    mock_embedding_service = Mock()
    mock_embedding_service.generate_embeddings_batch = AsyncMock(
        return_value=[[0.1] * 1536, [0.2] * 1536]
    )

    mock_session = AsyncMock()

    # Mock the app.models.document_chunk module
    mock_chunk_module = MagicMock()
    mock_chunk_class = MagicMock()
    mock_chunk_module.DocumentChunk = mock_chunk_class

    with patch('rag.indexer.TxtParser') as mock_parser, \
         patch.dict('sys.modules', {'app.models.document_chunk': mock_chunk_module}):
        mock_parser.return_value.parse.return_value = {"text": "test " * 100}

        indexer = DocumentIndexer(mock_embedding_service, mock_session)
        count = await indexer.index_document("proj1", "test.txt")

        assert count > 0
        assert mock_session.commit.called


@pytest.mark.asyncio
async def test_parse_document():
    """Test document parsing integration."""
    mock_service = Mock()
    mock_session = AsyncMock()

    with patch('rag.indexer.TxtParser') as mock_parser:
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
