"""Format converters for Excel, Images, and other document types."""
import os
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FormatConverter:
    """Handles conversion of various file formats to PDF."""
    
    # Supported formats
    OFFICE_FORMATS = {'.xls', '.xlsx', '.xlsm', '.ods', '.csv', '.tsv', '.doc', '.docx', '.ppt', '.pptx', '.odt', '.odp'}
    IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg'}
    
    @staticmethod
    def _check_libreoffice() -> bool:
        """Check if LibreOffice is installed."""
        try:
            result = subprocess.run(
                ['libreoffice', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def _check_imagemagick() -> bool:
        """Check if ImageMagick is installed."""
        try:
            result = subprocess.run(
                ['convert', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @classmethod
    def can_convert(cls, file_path: str) -> bool:
        """Check if file can be converted to PDF."""
        ext = Path(file_path).suffix.lower()
        
        if ext in cls.OFFICE_FORMATS:
            return cls._check_libreoffice()
        elif ext in cls.IMAGE_FORMATS:
            return cls._check_imagemagick()
        
        return False
    
    @classmethod
    def convert_to_pdf(cls, file_path: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Convert various file formats to PDF.
        
        Args:
            file_path: Path to input file
            output_dir: Optional output directory (uses temp if not specified)
            
        Returns:
            Path to generated PDF file, or None if conversion failed
        """
        ext = Path(file_path).suffix.lower()
        
        if ext in cls.OFFICE_FORMATS:
            return cls._convert_office_to_pdf(file_path, output_dir)
        elif ext in cls.IMAGE_FORMATS:
            return cls._convert_image_to_pdf(file_path, output_dir)
        else:
            logger.warning(f"Unsupported format for conversion: {ext}")
            return None
    
    @staticmethod
    def _convert_office_to_pdf(file_path: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Convert Office documents to PDF using LibreOffice.
        
        Args:
            file_path: Path to Office file
            output_dir: Output directory
            
        Returns:
            Path to PDF file or None
        """
        try:
            # Use temp directory if output_dir not specified
            if output_dir is None:
                output_dir = tempfile.gettempdir()
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Convert using LibreOffice headless mode
            logger.info(f"Converting Office document to PDF: {file_path}")
            
            result = subprocess.run(
                [
                    'libreoffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', output_dir,
                    file_path
                ],
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"LibreOffice conversion failed: {result.stderr}")
                return None
            
            # Find the generated PDF
            input_name = Path(file_path).stem
            pdf_path = os.path.join(output_dir, f"{input_name}.pdf")
            
            if os.path.exists(pdf_path):
                logger.info(f"Successfully converted to PDF: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"PDF not found after conversion: {pdf_path}")
                return None
            
        except subprocess.TimeoutExpired:
            logger.error(f"LibreOffice conversion timeout for {file_path}")
            return None
        except FileNotFoundError:
            logger.error("LibreOffice not found. Install with: brew install libreoffice (macOS) or apt-get install libreoffice (Linux)")
            return None
        except Exception as e:
            logger.error(f"Error converting Office document: {e}")
            return None
    
    @staticmethod
    def _convert_image_to_pdf(file_path: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Convert images to PDF using ImageMagick.
        
        Args:
            file_path: Path to image file
            output_dir: Output directory
            
        Returns:
            Path to PDF file or None
        """
        try:
            # Use temp directory if output_dir not specified
            if output_dir is None:
                output_dir = tempfile.gettempdir()
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename
            input_name = Path(file_path).stem
            pdf_path = os.path.join(output_dir, f"{input_name}.pdf")
            
            # Convert using ImageMagick
            logger.info(f"Converting image to PDF: {file_path}")
            
            result = subprocess.run(
                [
                    'convert',
                    file_path,
                    pdf_path
                ],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode != 0:
                logger.error(f"ImageMagick conversion failed: {result.stderr}")
                return None
            
            if os.path.exists(pdf_path):
                logger.info(f"Successfully converted to PDF: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"PDF not found after conversion: {pdf_path}")
                return None
            
        except subprocess.TimeoutExpired:
            logger.error(f"ImageMagick conversion timeout for {file_path}")
            return None
        except FileNotFoundError:
            logger.error("ImageMagick not found. Install with: brew install imagemagick (macOS) or apt-get install imagemagick (Linux)")
            return None
        except Exception as e:
            logger.error(f"Error converting image: {e}")
            return None
    
    @classmethod
    def get_supported_extensions(cls) -> set:
        """Get all supported file extensions."""
        return cls.OFFICE_FORMATS | cls.IMAGE_FORMATS


# Singleton instance
_converter = FormatConverter()

def convert_to_pdf(file_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    """Convenience function for converting files to PDF."""
    return _converter.convert_to_pdf(file_path, output_dir)

def can_convert(file_path: str) -> bool:
    """Check if file can be converted."""
    return _converter.can_convert(file_path)

def get_supported_extensions() -> set:
    """Get supported extensions."""
    return _converter.get_supported_extensions()
