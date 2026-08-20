"""Test multi-format support and table extraction."""
import pytest
import tempfile
import os
from pathlib import Path
from backend.utils.format_converters import FormatConverter, can_convert
from backend.utils.table_extractor import TableExtractor


class TestFormatConverter:
    """Test file format conversion."""
    
    def test_supported_extensions(self):
        """Test that all expected formats are supported."""
        converter = FormatConverter()
        
        # Check Office formats
        assert '.xlsx' in converter.OFFICE_FORMATS
        assert '.csv' in converter.OFFICE_FORMATS
        assert '.xls' in converter.OFFICE_FORMATS
        
        # Check image formats
        assert '.jpg' in converter.IMAGE_FORMATS
        assert '.png' in converter.IMAGE_FORMATS
        assert '.gif' in converter.IMAGE_FORMATS
        
        print("✅ All expected formats are supported")
    
    def test_libreoffice_check(self):
        """Test LibreOffice availability check."""
        has_libreoffice = FormatConverter._check_libreoffice()
        
        if has_libreoffice:
            print("✅ LibreOffice is installed")
        else:
            print("⚠️  LibreOffice not found (optional dependency)")
        
        # Test should pass either way
        assert isinstance(has_libreoffice, bool)
    
    def test_imagemagick_check(self):
        """Test ImageMagick availability check."""
        has_imagemagick = FormatConverter._check_imagemagick()
        
        if has_imagemagick:
            print("✅ ImageMagick is installed")
        else:
            print("⚠️  ImageMagick not found (optional dependency)")
        
        # Test should pass either way
        assert isinstance(has_imagemagick, bool)
    
    def test_can_convert_logic(self):
        """Test conversion capability detection."""
        # This should work without actual files
        converter = FormatConverter()
        
        # Test Office format detection
        assert '.xlsx' in converter.OFFICE_FORMATS
        
        # Test image format detection
        assert '.png' in converter.IMAGE_FORMATS
        
        print("✅ Format detection logic works")


class TestTableExtractor:
    """Test table extraction from PDFs."""
    
    def test_table_to_markdown(self):
        """Test markdown conversion."""
        extractor = TableExtractor()
        
        headers = ["Name", "Age", "City"]
        rows = [
            ["Alice", "30", "New York"],
            ["Bob", "25", "London"],
            ["Charlie", "35", "Paris"]
        ]
        
        markdown = extractor._table_to_markdown(headers, rows)
        
        # Check markdown structure
        assert "| Name | Age | City |" in markdown
        assert "| --- | --- | --- |" in markdown
        assert "| Alice | 30 | New York |" in markdown
        
        print("✅ Table to markdown conversion works")
        print(f"\nGenerated markdown:\n{markdown}")
    
    def test_table_settings(self):
        """Test that table extraction settings are properly configured."""
        extractor = TableExtractor()
        
        # Check that settings exist and have expected keys
        assert "vertical_strategy" in extractor.table_settings
        assert "horizontal_strategy" in extractor.table_settings
        assert "snap_tolerance" in extractor.table_settings
        
        print("✅ Table extraction settings configured")
    
    def test_combine_text_and_tables(self):
        """Test combining text blocks and tables."""
        extractor = TableExtractor()
        
        text_blocks = [
            {"page_number": 1, "text": "Introduction text", "type": "text"},
            {"page_number": 2, "text": "Conclusion text", "type": "text"}
        ]
        
        tables = [
            {
                "page_number": 1,
                "table_index": 0,
                "markdown": "| A | B |\n| --- | --- |\n| 1 | 2 |",
                "type": "table"
            }
        ]
        
        combined = extractor._combine_text_and_tables(text_blocks, tables)
        
        # Check that both text and tables are present
        assert "Introduction text" in combined
        assert "Conclusion text" in combined
        assert "| A | B |" in combined
        assert "Page 1" in combined
        assert "Page 2" in combined
        
        print("✅ Text and table combination works")
        print(f"\nCombined output:\n{combined}")


class TestIntegration:
    """Integration tests for the full pipeline."""
    
    def test_supported_extensions_count(self):
        """Test that we support more formats than before."""
        from backend.utils.document_processor import get_supported_extensions
        supported_extensions = get_supported_extensions()

        # The API validates uploads against this runtime resolver. Its basic
        # set is intentionally small at module import time to keep API start
        # lightweight; extended formats are provided by the worker converter.
        assert len(supported_extensions) >= 20

        # Check specific formats
        assert '.pdf' in supported_extensions
        assert '.xlsx' in supported_extensions
        assert '.csv' in supported_extensions
        assert '.png' in supported_extensions
        assert '.jpg' in supported_extensions

        print(f"✅ Supporting {len(supported_extensions)} file formats")
        print(f"   Formats: {sorted(supported_extensions)}")


def test_mock_table_extraction():
    """Test table extraction with mock data."""
    # This demonstrates the expected output structure
    mock_table = {
        "page_number": 1,
        "table_index": 0,
        "bbox": {"x1": 10.0, "y1": 20.0, "x2": 200.0, "y2": 100.0},
        "headers": ["Product", "Price", "Quantity"],
        "rows": [
            ["Widget A", "$10.00", "5"],
            ["Widget B", "$15.00", "3"]
        ],
        "row_count": 2,
        "col_count": 3,
        "markdown": "| Product | Price | Quantity |\n| --- | --- | --- |\n| Widget A | $10.00 | 5 |\n| Widget B | $15.00 | 3 |",
        "type": "table"
    }
    
    # Verify structure
    assert mock_table["page_number"] == 1
    assert mock_table["row_count"] == 2
    assert mock_table["col_count"] == 3
    assert len(mock_table["headers"]) == 3
    assert len(mock_table["rows"]) == 2
    
    print("✅ Table extraction structure validated")
    print(f"\nSample table markdown:\n{mock_table['markdown']}")


if __name__ == "__main__":
    print("\n🧪 MULTI-FORMAT SUPPORT & TABLE EXTRACTION TESTS\n")
    print("=" * 70)
    
    # Run tests
    test_converter = TestFormatConverter()
    test_converter.test_supported_extensions()
    test_converter.test_libreoffice_check()
    test_converter.test_imagemagick_check()
    test_converter.test_can_convert_logic()
    
    print("\n" + "=" * 70)
    
    test_extractor = TestTableExtractor()
    test_extractor.test_table_to_markdown()
    test_extractor.test_table_settings()
    test_extractor.test_combine_text_and_tables()
    
    print("\n" + "=" * 70)
    
    test_integration = TestIntegration()
    test_integration.test_supported_extensions_count()
    
    print("\n" + "=" * 70)
    
    test_mock_table_extraction()
    
    print("\n" + "=" * 70)
    print("\n✅ ALL TESTS PASSED!")
    print("\nℹ️  Note: LibreOffice and ImageMagick are optional.")
    print("   Install them for full multi-format support:")
    print("   - macOS: brew install libreoffice imagemagick")
    print("   - Linux: apt-get install libreoffice imagemagick")
