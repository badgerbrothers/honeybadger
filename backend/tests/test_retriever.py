"""Unit tests for document retrieval."""
import pytest
from unittest.mock import Mock, AsyncMock
from rag.retriever import DocumentRetriever


@pytest.mark.asyncio
async def test_retrieve_success():
    """Test successful similarity search."""
    mock_embedding_service = Mock()
    mock_embedding_service.generate_embedding = AsyncMock(
        return_value=[0.1] * 1536
    )

    mock_session = AsyncMock()
    mock_result = Mock()
    mock_chunk = Mock()
    mock_chunk.id = 1
    mock_chunk.content = "test content"
    mock_chunk.file_path = "test.txt"
    mock_chunk.chunk_index = 0
    mock_chunk.chunk_metadata = {}
    mock_result.all.return_value = [(mock_chunk, 0.85)]
    mock_session.execute = AsyncMock(return_value=mock_result)

    retriever = DocumentRetriever(mock_embedding_service, mock_session)
    results = await retriever.retrieve("query", "proj1", top_k=5, threshold=0.7)

    assert len(results) == 1
    assert results[0]["similarity"] == 0.85


@pytest.mark.asyncio
async def test_threshold_filtering():
    """Test score threshold filtering."""
    mock_service = Mock()
    mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

    mock_session = AsyncMock()
    mock_result = Mock()
    mock_chunk = Mock()
    mock_chunk.id = 1
    mock_chunk.content = "test"
    mock_chunk.file_path = "test.txt"
    mock_chunk.chunk_index = 0
    mock_chunk.chunk_metadata = {}
    mock_result.all.return_value = [(mock_chunk, 0.5)]
    mock_session.execute = AsyncMock(return_value=mock_result)

    retriever = DocumentRetriever(mock_service, mock_session)
    results = await retriever.retrieve("query", "proj1", threshold=0.7)

    assert len(results) == 0
