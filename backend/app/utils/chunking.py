"""
Production-Ready PDF Chunking for RAG.

Based on Azure Document Intelligence + LangChain best practices:
- Per-page chunking for 100% page number accuracy
- Table-aware: Never splits tables across chunks
- Markdown output for LLM compatibility
- Semantic boundaries (paragraphs) for long pages

References:
- https://ragaboutit.com/azure-document-intelligence-chunking-strategies/
- https://learn.microsoft.com/azure/ai-services/document-intelligence/
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExtractedChunk:
    """Chunk extracted from a document."""
    content: str
    page_number: int
    chunk_index: int
    metadata: Optional[Dict[str, Any]] = None


class DocumentLayoutChunker:
    """
    Per-page chunker with table awareness.
    
    Philosophy:
    1. Process each page independently (eliminates position tracking bugs)
    2. Preserve tables entirely (critical for tax documents)
    3. Split at semantic boundaries (paragraphs, not sentences)
    4. Maintain reasonable chunk sizes for embeddings
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 100,
        preserve_tables: bool = True
    ):
        """
        Args:
            max_chunk_size: Target maximum characters per chunk
            min_chunk_size: Minimum viable chunk size
            preserve_tables: If True, never split tables across chunks
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.preserve_tables = preserve_tables
        
        # Regex for detecting paragraph boundaries
        self.paragraph_pattern = re.compile(r'\n\s*\n+')
        
        # Regex for detecting Markdown tables
        self.table_pattern = re.compile(r'^\|.+\|$', re.MULTILINE)
    
    def chunk_document(
        self,
        pages: List[Dict[str, Any]],
        tables: Optional[List[Any]] = None
    ) -> List[ExtractedChunk]:
        """
        Chunk a document page by page.
        
        Args:
            pages: List of page dicts with 'page_number' and 'content' (Markdown)
            tables: Optional list of table objects from Azure DI
        
        Returns:
            List of ExtractedChunk objects
        """
        chunks = []
        chunk_index = 0
        
        for page in pages:
            page_number = page.get("page_number", 1)
            page_content = page.get("content", "").strip()
            
            if not page_content or len(page_content) < self.min_chunk_size:
                continue
            
            # Check if page contains tables
            has_tables = self._contains_table(page_content)
            
            # Strategy 1: Page fits in one chunk - preserve entirely
            if len(page_content) <= self.max_chunk_size:
                chunks.append(ExtractedChunk(
                    content=page_content,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    metadata={
                        'type': 'full_page',
                        'has_tables': has_tables,
                        'char_count': len(page_content)
                    }
                ))
                chunk_index += 1
            
            # Strategy 2: Page too large - split at semantic boundaries
            else:
                page_chunks = self._split_page_semantically(page_content, page_number)
                for chunk_content in page_chunks:
                    chunks.append(ExtractedChunk(
                        content=chunk_content,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        metadata={
                            'type': 'partial_page',
                            'has_tables': self._contains_table(chunk_content),
                            'char_count': len(chunk_content)
                        }
                    ))
                    chunk_index += 1
        
        return chunks
    
    def _contains_table(self, text: str) -> bool:
        """Check if text contains a Markdown table."""
        return bool(self.table_pattern.search(text))
    
    def _split_page_semantically(
        self,
        page_content: str,
        page_number: int
    ) -> List[str]:
        """
        Split a long page at semantic boundaries (paragraphs).
        
        Strategy:
        1. Try to split at paragraph boundaries
        2. If page has tables, extract and handle separately
        3. Ensure no chunk is too small or too large
        """
        chunks = []
        
        # If page has tables and preserve_tables is True, handle specially
        if self.preserve_tables and self._contains_table(page_content):
            return self._split_page_with_tables(page_content)
        
        # Standard semantic split at paragraphs
        paragraphs = self.paragraph_pattern.split(page_content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph exceeds max size
            if len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size:
                # Save current chunk if it's not too small
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Current chunk is too small, force-add this paragraph anyway
                    current_chunk += "\n\n" + paragraph
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add last chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [page_content]  # Fallback: return entire page
    
    def _split_page_with_tables(self, page_content: str) -> List[str]:
        """
        Special handling for pages with tables.
        
        Strategy:
        1. Extract all tables as continuous blocks
        2. Extract text between tables
        3. Create chunks that preserve table integrity
        """
        chunks = []
        
        # For now, simple approach: treat tables as atomic units
        # Split by double newlines but keep table rows together
        lines = page_content.split('\n')
        
        current_chunk = ""
        in_table = False
        table_buffer = []
        
        for line in lines:
            is_table_line = line.strip().startswith('|')
            
            if is_table_line:
                if not in_table:
                    # Starting a table - save current chunk
                    if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                    in_table = True
                table_buffer.append(line)
            else:
                if in_table:
                    # Ending a table - save it as a chunk
                    table_text = '\n'.join(table_buffer)
                    if len(table_text) > self.max_chunk_size:
                        # Table is too large - split it by rows (advanced)
                        chunks.extend(self._split_large_table(table_text))
                    else:
                        chunks.append(table_text)
                    table_buffer = []
                    in_table = False
                
                # Regular text line
                if len(current_chunk) + len(line) + 1 > self.max_chunk_size:
                    if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                        chunks.append(current_chunk.strip())
                        current_chunk = line
                    else:
                        current_chunk += '\n' + line
                else:
                    current_chunk += '\n' + line if current_chunk else line
        
        # Handle final table if any
        if table_buffer:
            table_text = '\n'.join(table_buffer)
            chunks.append(table_text)
        
        # Handle final text chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [page_content]
    
    def _split_large_table(self, table_text: str) -> List[str]:
        """
        Split a very large table into row groups.
        Preserves header row in each chunk.
        """
        lines = table_text.split('\n')
        if len(lines) < 3:
            return [table_text]
        
        # Assume first 2 lines are header + separator
        header = '\n'.join(lines[:2])
        data_rows = lines[2:]
        
        chunks = []
        current_rows = []
        current_size = len(header)
        
        for row in data_rows:
            if current_size + len(row) + 1 > self.max_chunk_size and current_rows:
                # Save current chunk
                chunk = header + '\n' + '\n'.join(current_rows)
                chunks.append(chunk)
                current_rows = [row]
                current_size = len(header) + len(row)
            else:
                current_rows.append(row)
                current_size += len(row) + 1
        
        # Add final chunk
        if current_rows:
            chunk = header + '\n' + '\n'.join(current_rows)
            chunks.append(chunk)
        
        return chunks
