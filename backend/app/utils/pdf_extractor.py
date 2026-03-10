"""
PDF Text Extractor for TaxIA using PyMuPDF4LLM

Optimized for extracting text from PDFs for LLM processing.
Supports:
- Markdown extraction (preserves structure)
- Table detection and formatting
- Image extraction (optional)
- Multi-column layout support
- Page chunking for better context

Perfect for AEAT notifications and tax documents.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import io

logger = logging.getLogger(__name__)

# Try to import pymupdf4llm
try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False
    logger.warning("pymupdf4llm not available. Install with: pip install pymupdf4llm")


@dataclass
class PDFPage:
    """Represents a single page from a PDF."""
    page_number: int
    text: str
    metadata: Dict[str, Any]


@dataclass
class PDFExtractionResult:
    """Result of PDF text extraction."""
    success: bool
    pages: List[PDFPage]
    total_pages: int
    total_chars: int
    markdown_text: str
    error: Optional[str] = None


class PDFTextExtractor:
    """
    Extract text from PDFs optimized for LLM processing.
    
    Uses PyMuPDF4LLM for:
    - Markdown conversion (preserves structure)
    - Table detection
    - Multi-column support
    - Header/footer detection
    """
    
    def __init__(
        self,
        extract_images: bool = False,
        page_chunks: bool = True,
        dpi: int = 150
    ):
        """
        Initialize PDF text extractor.
        
        Args:
            extract_images: Whether to extract images (default: False for speed)
            page_chunks: Return text as page chunks (default: True)
            dpi: DPI for image extraction (default: 150)
        """
        if not PYMUPDF4LLM_AVAILABLE:
            raise ImportError("pymupdf4llm is required. Install with: pip install pymupdf4llm")
        
        self.extract_images = extract_images
        self.page_chunks = page_chunks
        self.dpi = dpi
    
    async def extract_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf"
    ) -> PDFExtractionResult:
        """
        Extract text from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename (for logging)
            
        Returns:
            PDFExtractionResult with extracted text
        """
        import tempfile
        import os
        
        try:
            # PyMuPDF4LLM requires a file path, not BytesIO
            # Create a temporary file (don't delete automatically on Windows)
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf')
            
            try:
                # Write PDF bytes to temp file
                os.write(tmp_fd, pdf_bytes)
                os.close(tmp_fd)  # Close file descriptor before pymupdf4llm uses it
                
                # Extract markdown text
                if self.page_chunks:
                    # Extract as page chunks (list of dicts)
                    result = pymupdf4llm.to_markdown(
                        tmp_path,
                        page_chunks=True,
                        write_images=self.extract_images,
                        dpi=self.dpi
                    )
                    
                    # Process page chunks
                    pages = []
                    full_markdown = []
                    
                    for idx, page_data in enumerate(result):
                        page_text = page_data.get("text", "")
                        page_metadata = page_data.get("metadata", {})
                        
                        pages.append(PDFPage(
                            page_number=idx + 1,
                            text=page_text,
                            metadata=page_metadata
                        ))
                        
                        full_markdown.append(f"## Página {idx + 1}\n\n{page_text}")
                    
                    markdown_text = "\n\n".join(full_markdown)
                    total_pages = len(pages)
                    total_chars = sum(len(p.text) for p in pages)
                    
                else:
                    # Extract as single markdown string
                    markdown_text = pymupdf4llm.to_markdown(
                        tmp_path,
                        write_images=self.extract_images,
                        dpi=self.dpi
                    )
                    
                    # Create single page
                    pages = [PDFPage(
                        page_number=1,
                        text=markdown_text,
                        metadata={}
                    )]
                    
                    total_pages = 1
                    total_chars = len(markdown_text)
                
                logger.info(f"✅ Extracted {total_chars} chars from {total_pages} pages: {filename}")
                
                return PDFExtractionResult(
                    success=True,
                    pages=pages,
                    total_pages=total_pages,
                    total_chars=total_chars,
                    markdown_text=markdown_text
                )
            
            finally:
                # Clean up temp file (Windows-safe)
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not delete temp file {tmp_path}: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"❌ PDF extraction failed for {filename}: {e}")
            return PDFExtractionResult(
                success=False,
                pages=[],
                total_pages=0,
                total_chars=0,
                markdown_text="",
                error=str(e)
            )
    
    async def extract_from_file(
        self,
        file_path: str
    ) -> PDFExtractionResult:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDFExtractionResult with extracted text
        """
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            
            filename = Path(file_path).name
            return await self.extract_from_bytes(pdf_bytes, filename)
            
        except Exception as e:
            logger.error(f"❌ Failed to read PDF file {file_path}: {e}")
            return PDFExtractionResult(
                success=False,
                pages=[],
                total_pages=0,
                total_chars=0,
                markdown_text="",
                error=str(e)
            )
    
    def get_page_text(self, result: PDFExtractionResult, page_number: int) -> Optional[str]:
        """
        Get text from a specific page.
        
        Args:
            result: PDFExtractionResult from extraction
            page_number: Page number (1-indexed)
            
        Returns:
            Page text or None if page not found
        """
        for page in result.pages:
            if page.page_number == page_number:
                return page.text
        return None
    
    def get_summary(self, result: PDFExtractionResult) -> str:
        """
        Get a summary of the extraction result.
        
        Args:
            result: PDFExtractionResult from extraction
            
        Returns:
            Human-readable summary
        """
        if not result.success:
            return f"❌ Extraction failed: {result.error}"
        
        return (
            f"✅ Extracted {result.total_pages} pages, "
            f"{result.total_chars:,} characters"
        )


# Global extractor instance
_pdf_extractor: Optional[PDFTextExtractor] = None


def get_pdf_extractor() -> PDFTextExtractor:
    """Get global PDF extractor instance."""
    global _pdf_extractor
    if _pdf_extractor is None:
        _pdf_extractor = PDFTextExtractor(
            extract_images=False,  # Faster, images not needed for AEAT docs
            page_chunks=True,      # Better for LLM context
            dpi=150                # Good balance of quality/speed
        )
    return _pdf_extractor


async def extract_pdf_text(pdf_bytes: bytes, filename: str = "document.pdf") -> PDFExtractionResult:
    """
    Convenience function to extract text from PDF bytes.

    Args:
        pdf_bytes: PDF file content
        filename: Original filename

    Returns:
        PDFExtractionResult with extracted text
    """
    extractor = get_pdf_extractor()
    return await extractor.extract_from_bytes(pdf_bytes, filename)


async def extract_pdf_text_plain(pdf_bytes: bytes, filename: str = "document.pdf") -> PDFExtractionResult:
    """
    Extract PDF text using PyMuPDF plain text mode (page.get_text('text')).

    This is much better for tabular documents like payslips and invoices
    where pymupdf4llm's markdown conversion destroys the column layout.
    The plain text preserves the spatial reading order which makes
    regex extraction reliable.

    Args:
        pdf_bytes: PDF file content
        filename: Original filename

    Returns:
        PDFExtractionResult with extracted text
    """
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        full_text_parts = []

        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(PDFPage(
                page_number=i + 1,
                text=text,
                metadata={}
            ))
            full_text_parts.append(f"=== PAGINA {i + 1} ===\n{text}")

        doc.close()

        full_text = "\n\n".join(full_text_parts)
        total_chars = sum(len(p.text) for p in pages)

        logger.info(f"Extracted {total_chars} chars (plain text) from {len(pages)} pages: {filename}")

        return PDFExtractionResult(
            success=True,
            pages=pages,
            total_pages=len(pages),
            total_chars=total_chars,
            markdown_text=full_text
        )

    except Exception as e:
        logger.error(f"Plain text PDF extraction failed for {filename}: {e}")
        return PDFExtractionResult(
            success=False,
            pages=[],
            total_pages=0,
            total_chars=0,
            markdown_text="",
            error=str(e)
        )
