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

    retriever = DocumentRetriever(mock_embedding_service, mock_session)

    # Mock the internal search method
    retriever._search_similar_chunks = AsyncMock(return_value=[
        {
            "id": 1,
            "content": "test content",
            "file_path": "test.txt",
            "chunk_index": 0,
            "similarity": 0.85,
            "metadata": {}
        }
    ])

    results = await retriever.retrieve("query", "proj1", top_k=5, threshold=0.7)

    assert len(results) == 1
    assert results[0]["similarity"] == 0.85


@pytest.mark.asyncio
async def test_threshold_filtering():
    """Test score threshold filtering."""
    mock_service = Mock()
    mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

    mock_session = AsyncMock()

    retriever = DocumentRetriever(mock_service, mock_session)

    # Mock the internal search method to return empty results
    retriever._search_similar_chunks = AsyncMock(return_value=[])

    results = await retriever.retrieve("query", "proj1", threshold=0.7)

    assert len(results) == 0
