"""Tests for document processing utilities."""
import pytest
from insightdocs.utils.document_processor import DocumentProcessor


@pytest.fixture
def processor():
    """Create document processor instance."""
    return DocumentProcessor()


@pytest.mark.asyncio
async def test_chunk_text_basic(processor):
    """Test basic text chunking."""
    text = "This is sentence one. This is sentence two. This is sentence three."
    
    chunks = await processor.chunk_text(text, chunk_size=50, overlap=10)
    
    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)


@pytest.mark.asyncio
async def test_chunk_text_empty(processor):
    """Test chunking empty text."""
    chunks = await processor.chunk_text("", chunk_size=100)
    
    assert chunks == []


@pytest.mark.asyncio
async def test_chunk_text_small(processor):
    """Test chunking text smaller than chunk size."""
    text = "Short text."
    
    chunks = await processor.chunk_text(text, chunk_size=100)
    
    assert len(chunks) == 1
    assert chunks[0] == text


@pytest.mark.asyncio
async def test_parse_text_file(processor, tmp_path):
    """Test parsing text file."""
    # Create temporary text file
    test_file = tmp_path / "test.txt"
    test_content = "Test content for parsing"
    test_file.write_text(test_content)
    
    result = await processor.parse_document(str(test_file))
    
    assert result["text"] == test_content
    assert result["metadata"]["type"] == "text"
    assert result["metadata"]["char_count"] == len(test_content)
