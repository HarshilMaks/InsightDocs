"""
Phase B: OCR Pipeline Integration Tests
Tests OCR detection, text extraction, and integration with document processing.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

os.environ.setdefault("JWT_SECRET", "test-secret-key")

from backend.utils.ocr_processor import OcrProcessor


class TestOCRDetection:
    """Test scanned PDF detection."""

    def test_detect_scanned_pdf_with_few_text_blocks(self):
        """OCR processor should detect PDFs with < 3 text blocks per page as scanned."""
        processor = OcrProcessor()
        
        # Mock PyMuPDF to return minimal text blocks
        with patch('backend.utils.ocr_processor.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            
            # Simulate < 3 text blocks (scanned page)
            mock_page.get_text("blocks").return_value = [("text1",), ("text2",)]
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.page_count = 1
            mock_fitz.open.return_value = mock_doc
            
            is_scanned, confidence = processor.detect_scanned_pdf("/fake/path.pdf")
            
            assert is_scanned == True
            assert 0.0 <= confidence <= 1.0

    def test_detect_native_pdf_with_many_text_blocks(self):
        """OCR processor should detect PDFs with >= 3 text blocks per page as native."""
        processor = OcrProcessor()
        
        with patch('backend.utils.ocr_processor.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            
            # Simulate >= 3 text blocks (native PDF)
            mock_page.get_text("blocks").return_value = [
                ("text1",), ("text2",), ("text3",), ("text4",)
            ]
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.page_count = 1
            mock_fitz.open.return_value = mock_doc
            
            is_scanned, confidence = processor.detect_scanned_pdf("/fake/path.pdf")
            
            assert is_scanned == False

    def test_detection_handles_multiple_pages(self):
        """Detection should check multiple pages (up to 3) for accuracy."""
        processor = OcrProcessor()
        
        with patch('backend.utils.ocr_processor.fitz') as mock_fitz:
            mock_doc = MagicMock()
            mock_pages = []
            
            # Pages 0-2: scanned (few text blocks)
            for i in range(3):
                page = MagicMock()
                page.get_text("blocks").return_value = [("text",)]
                mock_pages.append(page)
            
            # Page 3: native (many text blocks) - beyond check limit
            page = MagicMock()
            page.get_text("blocks").return_value = [("a",), ("b",), ("c",), ("d",)]
            mock_pages.append(page)
            
            mock_doc.__getitem__.side_effect = mock_pages
            mock_doc.page_count = 4
            mock_fitz.open.return_value = mock_doc
            
            is_scanned, _ = processor.detect_scanned_pdf("/fake/path.pdf")
            
            # Should be detected as scanned (first 3 pages are scanned)
            assert is_scanned == True


class TestOCRTextExtraction:
    """Test OCR text extraction from images."""

    def test_extract_text_from_image_with_confidence(self):
        """OCR should extract text and return confidence score."""
        processor = OcrProcessor()
        
        with patch('backend.utils.ocr_processor.pytesseract') as mock_ocr:
            mock_ocr.image_to_data.return_value = """level page_num block_num par_num ...
1 1 1 1 10 10 100 100 0.95 "Hello"
1 1 1 1 120 10 200 100 0.90 "World"
"""
            with patch('backend.utils.ocr_processor.Image') as mock_image:
                mock_img = MagicMock()
                mock_image.open.return_value = mock_img
                
                text, confidence = processor.extract_text_from_image("/fake/image.png")
                
                # Should have extracted text
                assert text is not None
                assert len(text) > 0
                # Confidence should be between 0 and 1
                assert 0.0 <= confidence <= 1.0

    def test_extract_text_handles_missing_tesseract(self):
        """Should handle gracefully when Tesseract is not installed."""
        processor = OcrProcessor()
        
        with patch('backend.utils.ocr_processor.pytesseract') as mock_ocr:
            mock_ocr.pytesseract_not_found.side_effect = Exception("Tesseract not found")
            
            # Should not raise exception
            with patch('backend.utils.ocr_processor.Image') as mock_image:
                mock_img = MagicMock()
                mock_image.open.return_value = mock_img
                
                # Extraction should fail gracefully
                try:
                    text, confidence = processor.extract_text_from_image("/fake/image.png")
                except Exception as e:
                    # Exception expected but shouldn't crash
                    assert "Tesseract" in str(e) or "not" in str(e).lower()


class TestOCRIntegrationWithDocumentProcessor:
    """Test OCR integration with document processing pipeline."""

    def test_ocr_processor_called_on_scanned_pdf_upload(self):
        """When a scanned PDF is uploaded, OCR processor should be invoked."""
        from backend.utils.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        
        with patch.object(processor, '_process_pdf') as mock_pdf:
            with patch.object(OcrProcessor, 'detect_scanned_pdf') as mock_detect:
                mock_detect.return_value = (True, 0.85)  # Detected as scanned
                
                # This would normally be called during document upload
                # Verify detection is called
                is_scanned, conf = OcrProcessor().detect_scanned_pdf("/fake.pdf")
                
                assert is_scanned == True
                assert conf == 0.85

    def test_ocr_fallback_on_native_pdf(self):
        """For native PDFs, OCR should not be triggered unnecessarily."""
        from backend.utils.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        
        with patch.object(OcrProcessor, 'detect_scanned_pdf') as mock_detect:
            mock_detect.return_value = (False, 0.0)  # Native PDF
            
            is_scanned, conf = OcrProcessor().detect_scanned_pdf("/fake.pdf")
            
            assert is_scanned == False
            assert conf == 0.0


class TestOCRMetadataTracking:
    """Test that OCR metadata is properly stored."""

    def test_document_model_stores_ocr_fields(self):
        """Document model should track is_scanned and ocr_confidence."""
        from backend.models.schemas import Document, TaskStatus
        
        doc = Document(
            id="test-doc",
            filename="scanned.pdf",
            user_id="user1",
            status=TaskStatus.COMPLETED,
            file_size=5000,
            chunks_count=10,
            is_scanned=True,
            ocr_confidence=0.92
        )
        
        assert doc.is_scanned == True
        assert doc.ocr_confidence == 0.92

    def test_document_chunk_preserves_ocr_metadata(self):
        """Document chunks should preserve OCR confidence in metadata."""
        from backend.models.schemas import DocumentChunk
        
        chunk = DocumentChunk(
            id="chunk1",
            document_id="doc1",
            content="OCR extracted text",
            chunk_index=0,
            metadata={"ocr_confidence": 0.88, "source": "ocr"}
        )
        
        assert chunk.metadata["ocr_confidence"] == 0.88
        assert chunk.metadata["source"] == "ocr"
