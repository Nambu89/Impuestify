"""
Azure Document Intelligence Client for TaxIA

Provides PDF text extraction using Azure AI Document Intelligence.
Replaces the local pypdf extraction with cloud-based AI extraction.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """Extracted page content"""
    page_number: int
    content: str
    tables: List[Dict[str, Any]]
    figures: List[Dict[str, Any]]


@dataclass
class ExtractedDocument:
    """Extracted document content"""
    filename: str
    total_pages: int
    pages: List[ExtractedPage]
    full_content: str
    metadata: Dict[str, Any]


class DocumentIntelligenceExtractor:
    """
    Azure Document Intelligence client for PDF extraction.
    
    Uses the Layout model for structured text extraction
    with table and figure detection.
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None
    ):
        """
        Initialize Document Intelligence client.
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            key: Azure Document Intelligence API key
        """
        self.endpoint = endpoint or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.key = key or os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        
        self._client: Optional[DocumentIntelligenceClient] = None
        
        if not all([self.endpoint, self.key]):
            logger.warning("Document Intelligence credentials not configured")
    
    def _get_client(self) -> DocumentIntelligenceClient:
        """Get or create the Document Intelligence client."""
        if self._client is None:
            if not all([self.endpoint, self.key]):
                raise ValueError("Document Intelligence endpoint and key are required")
            
            self._client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )
            logger.info("Document Intelligence client initialized")
        
        return self._client
    
    def extract_from_file(self, file_path: str) -> ExtractedDocument:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            ExtractedDocument with content and metadata
        """
        client = self._get_client()
        
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        return self.extract_from_bytes(file_content, os.path.basename(file_path))
    
    def extract_from_bytes(self, content: bytes, filename: str = "document.pdf") -> ExtractedDocument:
        """
        Extract text from PDF bytes.
        
        Args:
            content: PDF file content as bytes
            filename: Original filename for reference
            
        Returns:
            ExtractedDocument with content and metadata
        """
        client = self._get_client()
        
        try:
            # Use the prebuilt-layout model for structured extraction
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                analyze_request=content,
                content_type="application/pdf"
            )
            
            result: AnalyzeResult = poller.result()
            
            return self._process_result(result, filename)
            
        except Exception as e:
            logger.error(f"Document extraction failed: {e}")
            raise
    
    def extract_from_url(self, url: str, filename: str = "document.pdf") -> ExtractedDocument:
        """
        Extract text from a PDF at a URL.
        
        Args:
            url: URL to the PDF file
            filename: Filename for reference
            
        Returns:
            ExtractedDocument with content and metadata
        """
        client = self._get_client()
        
        try:
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                analyze_request=AnalyzeDocumentRequest(url_source=url)
            )
            
            result: AnalyzeResult = poller.result()
            
            return self._process_result(result, filename)
            
        except Exception as e:
            logger.error(f"Document extraction from URL failed: {e}")
            raise
    
    def _process_result(self, result: AnalyzeResult, filename: str) -> ExtractedDocument:
        """
        Process the analysis result into structured content.
        
        Args:
            result: AnalyzeResult from Document Intelligence
            filename: Original filename
            
        Returns:
            ExtractedDocument with processed content
        """
        pages = []
        full_content_parts = []
        
        # Process each page
        for page in result.pages:
            page_content_parts = []
            
            # Extract lines of text
            if page.lines:
                for line in page.lines:
                    page_content_parts.append(line.content)
            
            page_content = "\n".join(page_content_parts)
            full_content_parts.append(page_content)
            
            # Extract tables from this page
            page_tables = []
            if result.tables:
                for table in result.tables:
                    # Check if table belongs to this page
                    if hasattr(table, 'bounding_regions') and table.bounding_regions:
                        for region in table.bounding_regions:
                            if region.page_number == page.page_number:
                                table_data = self._extract_table(table)
                                page_tables.append(table_data)
            
            # Extract figures from this page
            page_figures = []
            if hasattr(result, 'figures') and result.figures:
                for figure in result.figures:
                    if hasattr(figure, 'bounding_regions') and figure.bounding_regions:
                        for region in figure.bounding_regions:
                            if region.page_number == page.page_number:
                                page_figures.append({
                                    "caption": getattr(figure, 'caption', None),
                                    "span": getattr(figure, 'spans', [])
                                })
            
            pages.append(ExtractedPage(
                page_number=page.page_number,
                content=page_content,
                tables=page_tables,
                figures=page_figures
            ))
        
        # Build metadata
        metadata = {
            "model_id": result.model_id,
            "api_version": result.api_version if hasattr(result, 'api_version') else None,
            "content_format": result.content_format if hasattr(result, 'content_format') else None,
        }
        
        return ExtractedDocument(
            filename=filename,
            total_pages=len(pages),
            pages=pages,
            full_content="\n\n".join(full_content_parts),
            metadata=metadata
        )
    
    def _extract_table(self, table) -> Dict[str, Any]:
        """
        Extract table content into structured format.
        
        Args:
            table: Table object from Document Intelligence
            
        Returns:
            Dictionary with table structure and content
        """
        rows = []
        
        if hasattr(table, 'cells') and table.cells:
            # Group cells by row
            row_dict = {}
            for cell in table.cells:
                row_idx = cell.row_index
                if row_idx not in row_dict:
                    row_dict[row_idx] = {}
                row_dict[row_idx][cell.column_index] = cell.content
            
            # Convert to list of lists
            for row_idx in sorted(row_dict.keys()):
                row = []
                for col_idx in sorted(row_dict[row_idx].keys()):
                    row.append(row_dict[row_idx][col_idx])
                rows.append(row)
        
        return {
            "row_count": table.row_count if hasattr(table, 'row_count') else len(rows),
            "column_count": table.column_count if hasattr(table, 'column_count') else (len(rows[0]) if rows else 0),
            "rows": rows
        }


# Global instance
_doc_extractor: Optional[DocumentIntelligenceExtractor] = None


def get_document_extractor() -> DocumentIntelligenceExtractor:
    """
    Get the global document extractor instance.
    
    Returns:
        DocumentIntelligenceExtractor instance
    """
    global _doc_extractor
    
    if _doc_extractor is None:
        _doc_extractor = DocumentIntelligenceExtractor()
    
    return _doc_extractor
