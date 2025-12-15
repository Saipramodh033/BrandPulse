"""
PDF Utilities - Text Extraction
===============================
Extract text from PDF files (used in dashboard when admin uploads)
"""

import logging
import io
from typing import Optional

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text content from PDF file.
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        Extracted text as string
        
    Raises:
        ValueError: If PDF is encrypted, corrupted, or empty
    """
    logger.info(f"📄 Extracting text from PDF ({len(pdf_bytes)} bytes)")
    
    try:
        # Create reader from bytes
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        # Check encryption
        if reader.is_encrypted:
            raise ValueError("PDF is password-protected - cannot extract text")
        
        # Extract from all pages
        extracted_text = ""
        page_count = len(reader.pages)
        
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text.strip():
                    extracted_text += f"\n\n=== Page {page_num + 1} ===\n{page_text}"
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract page {page_num + 1}: {e}")
                continue
        
        # Validate result
        if not extracted_text.strip():
            raise ValueError(
                "No text found in PDF. "
                "This may be an image-based PDF requiring OCR."
            )
        
        logger.info(f"✅ Extracted {len(extracted_text)} characters from {page_count} pages")
        
        return extracted_text.strip()
        
    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"❌ PDF extraction failed: {e}")
        raise ValueError(f"Failed to process PDF: {str(e)}")


def validate_pdf_file(pdf_bytes: bytes, max_size_mb: int = 10) -> Optional[str]:
    """
    Validate PDF file before processing.
    
    Args:
        pdf_bytes: PDF file bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        Error message if invalid, None if valid
    """
    # Check size
    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return f"PDF too large ({size_mb:.1f}MB). Maximum: {max_size_mb}MB"
    
    # Check if actually PDF (magic bytes)
    if not pdf_bytes.startswith(b'%PDF'):
        return "File is not a valid PDF"
    
    # Try to open
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        if len(reader.pages) == 0:
            return "PDF has no pages"
        
        if reader.is_encrypted:
            return "PDF is password-protected"
        
    except Exception as e:
        return f"Invalid or corrupted PDF: {str(e)}"
    
    return None