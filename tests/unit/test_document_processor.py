"""Tests for document processing utilities."""
import pytest
from backend.utils.document_processor import DocumentProcessor


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
    # Chunks are now dicts with 'text' key (bbox upgrade)
    assert all(isinstance(chunk, dict) and 'text' in chunk for chunk in chunks)


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
    # Chunks are now dicts with 'text' key (bbox upgrade)
    assert chunks[0]['text'] == text


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


@pytest.mark.asyncio
async def test_pdf_uses_plain_text_fallback_when_pymupdf_is_unavailable(monkeypatch):
    import backend.utils.pdf_parser_enhanced as enhanced_parser
    import backend.utils.document_processor as processor_module

    monkeypatch.setattr(enhanced_parser, "FITZ_AVAILABLE", False)
    monkeypatch.setattr(
        processor_module,
        "extract_text_and_tables",
        lambda _path: {
            "combined_text": "Text extracted by pdfplumber.",
            "tables": [],
            "text_blocks": [{"text": "Text extracted by pdfplumber."}],
        },
    )

    processor = DocumentProcessor()
    result = await processor._parse_pdf_file("without-pymupdf.pdf")

    assert result["text"] == "Text extracted by pdfplumber."
    assert result["blocks"] == []
    assert result["metadata"]["has_spatial_data"] is False
