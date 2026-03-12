"""Unit tests for embedding service."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from rag.embeddings import EmbeddingService


@pytest.mark.asyncio
async def test_generate_embedding_success():
    """Test successful embedding generation."""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1] * 1536)]

    with patch('rag.embeddings.AsyncOpenAI') as mock_client:
        mock_client.return_value.embeddings.create = AsyncMock(return_value=mock_response)

        service = EmbeddingService(api_key="test-key")
        result = await service.generate_embedding("test text")

        assert len(result) == 1536
        assert isinstance(result[0], float)


@pytest.mark.asyncio
async def test_generate_embeddings_batch():
    """Test batch embedding generation."""
    mock_response = Mock()
    mock_response.data = [
        Mock(embedding=[0.1] * 1536),
        Mock(embedding=[0.2] * 1536)
    ]

    with patch('rag.embeddings.AsyncOpenAI') as mock_client:
        mock_client.return_value.embeddings.create = AsyncMock(return_value=mock_response)

        service = EmbeddingService(api_key="test-key")
        results = await service.generate_embeddings_batch(["text1", "text2"])

        assert len(results) == 2
        assert len(results[0]) == 1536


@pytest.mark.asyncio
async def test_embedding_dimension():
    """Verify embedding dimension is 1536."""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1] * 1536)]

    with patch('rag.embeddings.AsyncOpenAI') as mock_client:
        mock_client.return_value.embeddings.create = AsyncMock(return_value=mock_response)

        service = EmbeddingService(api_key="test-key")
        result = await service.generate_embedding("test")

        assert len(result) == 1536


@pytest.mark.asyncio
async def test_batch_size_limit():
    """Test batch size limit enforcement."""
    service = EmbeddingService(api_key="test-key")

    with pytest.raises(ValueError, match="Batch size cannot exceed 2048"):
        await service.generate_embeddings_batch(["text"] * 2049)
