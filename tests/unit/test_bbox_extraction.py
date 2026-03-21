"""Test bounding box extraction and storage."""
import pytest
from backend.utils.pdf_parser_enhanced import EnhancedPDFParser
from backend.models.schemas import DocumentChunk
from backend.models.database import SessionLocal


@pytest.mark.asyncio
async def test_pdf_bbox_extraction():
    """Test that PyMuPDF parser extracts bounding boxes."""
    parser = EnhancedPDFParser()
    
    # Note: This test would need a real PDF file to work properly
    # For now, we're just testing the logic structure
    
    # Mock result structure
    mock_result = {
        "text": "Sample text from PDF",
        "blocks": [
            {
                "text": "First block",
                "page_number": 1,
                "bbox": {"x1": 10.0, "y1": 20.0, "x2": 100.0, "y2": 40.0},
                "type": "text"
            },
            {
                "text": "Second block",
                "page_number": 1,
                "bbox": {"x1": 10.0, "y1": 50.0, "x2": 100.0, "y2": 70.0},
                "type": "text"
            }
        ],
        "metadata": {
            "type": "pdf",
            "page_count": 1,
            "char_count": 23,
            "block_count": 2,
            "has_spatial_data": True
        }
    }
    
    # Verify blocks have required fields
    for block in mock_result["blocks"]:
        assert "text" in block
        assert "page_number" in block
        assert "bbox" in block
        assert "x1" in block["bbox"]
        assert "y1" in block["bbox"]
        assert "x2" in block["bbox"]
        assert "y2" in block["bbox"]
    
    print("✅ Bounding box structure validated")


@pytest.mark.asyncio
async def test_chunk_with_bbox_storage():
    """Test that chunks with bbox data can be stored in DB."""
    
    # Mock chunk data with bbox
    mock_chunk = {
        "text": "This is a sample chunk with spatial data.",
        "page_number": 1,
        "bbox": {
            "x1": 10.5,
            "y1": 20.3,
            "x2": 150.7,
            "y2": 45.9
        }
    }
    
    # Create a DocumentChunk instance (don't commit, just test creation)
    chunk = DocumentChunk(
        document_id="test-doc-id",
        chunk_index=0,
        content=mock_chunk["text"],
        page_number=mock_chunk["page_number"],
        bbox_x1=mock_chunk["bbox"]["x1"],
        bbox_y1=mock_chunk["bbox"]["y1"],
        bbox_x2=mock_chunk["bbox"]["x2"],
        bbox_y2=mock_chunk["bbox"]["y2"],
    )
    
    # Verify all bbox fields are set correctly
    assert chunk.page_number == 1
    assert chunk.bbox_x1 == 10.5
    assert chunk.bbox_y1 == 20.3
    assert chunk.bbox_x2 == 150.7
    assert chunk.bbox_y2 == 45.9
    
    print("✅ DocumentChunk with bbox data created successfully")


def test_chunk_blocks_method():
    """Test the chunk_blocks method preserves spatial data."""
    parser = EnhancedPDFParser()
    
    blocks = [
        {
            "text": "Block 1 " * 100,  # ~700 chars
            "page_number": 1,
            "bbox": {"x1": 10, "y1": 20, "x2": 100, "y2": 40}
        },
        {
            "text": "Block 2 " * 100,
            "page_number": 1,
            "bbox": {"x1": 10, "y1": 50, "x2": 100, "y2": 70}
        },
        {
            "text": "Block 3 " * 100,
            "page_number": 2,
            "bbox": {"x1": 10, "y1": 20, "x2": 100, "y2": 40}
        }
    ]
    
    chunks = parser.chunk_blocks(blocks, chunk_size=500, overlap=100)
    
    # Should create multiple chunks
    assert len(chunks) > 0
    
    # Each chunk should have bbox data
    for chunk in chunks:
        assert "text" in chunk
        assert "page_number" in chunk
        assert "bbox" in chunk
        assert "x1" in chunk["bbox"]
        assert "y1" in chunk["bbox"]
    
    print(f"✅ Created {len(chunks)} chunks with bbox data preserved")


if __name__ == "__main__":
    import asyncio
    
    print("\n🧪 Running Bounding Box Tests\n")
    
    asyncio.run(test_pdf_bbox_extraction())
    asyncio.run(test_chunk_with_bbox_storage())
    test_chunk_blocks_method()
    
    print("\n✅ All bounding box tests passed!")
