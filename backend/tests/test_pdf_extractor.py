"""
Tests for PDF Text Extractor using PyMuPDF4LLM
"""
import pytest
import asyncio
from pathlib import Path


class TestPDFExtractor:
    """Tests for PDF text extraction"""
    
    @pytest.mark.asyncio
    async def test_pdf_extractor_initialization(self):
        """Test that PDF extractor initializes correctly"""
        from app.utils.pdf_extractor import PDFTextExtractor, PYMUPDF4LLM_AVAILABLE
        
        if not PYMUPDF4LLM_AVAILABLE:
            pytest.skip("pymupdf4llm not installed")
        
        extractor = PDFTextExtractor(
            extract_images=False,
            page_chunks=True,
            dpi=150
        )
        
        assert extractor is not None
        assert extractor.extract_images == False
        assert extractor.page_chunks == True
        assert extractor.dpi == 150
        
        print("\n[PASS] PDF Extractor: Initialized successfully")
    
    @pytest.mark.asyncio
    async def test_pdf_extraction_simple(self):
        """Test extraction from a simple PDF"""
        from app.utils.pdf_extractor import get_pdf_extractor, PYMUPDF4LLM_AVAILABLE
        
        if not PYMUPDF4LLM_AVAILABLE:
            pytest.skip("pymupdf4llm not installed")
        
        # Create a minimal PDF for testing
        # This is a simple PDF with "Hello World"
        minimal_pdf = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""
        
        extractor = get_pdf_extractor()
        result = await extractor.extract_from_bytes(minimal_pdf, "test.pdf")
        
        assert result.success, f"Extraction failed: {result.error}"
        assert result.total_pages >= 1
        assert len(result.markdown_text) > 0
        
        print(f"\n[PASS] PDF Extractor: Extracted {result.total_chars} chars from {result.total_pages} pages")
    
    def test_pdf_extractor_summary(self):
        """Test summary generation"""
        from app.utils.pdf_extractor import PDFTextExtractor, PDFExtractionResult, PDFPage, PYMUPDF4LLM_AVAILABLE
        
        if not PYMUPDF4LLM_AVAILABLE:
            pytest.skip("pymupdf4llm not installed")
        
        extractor = PDFTextExtractor()
        
        # Create mock result
        result = PDFExtractionResult(
            success=True,
            pages=[
                PDFPage(page_number=1, text="Page 1 content", metadata={}),
                PDFPage(page_number=2, text="Page 2 content", metadata={})
            ],
            total_pages=2,
            total_chars=30,
            markdown_text="# Test\n\nPage 1 content\n\nPage 2 content"
        )
        
        summary = extractor.get_summary(result)
        
        assert "2 pages" in summary
        assert "30 characters" in summary
        
        print(f"\n[PASS] PDF Extractor: Summary generation works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
