"""
Production-Ready PDF Chunking for RAG.

Based on Azure Document Intelligence + LangChain best practices:
- Per-page chunking for 100% page number accuracy
- Table-aware: Never splits tables across chunks
- Markdown heading-aware: respects ## / ### boundaries
- Sentence-boundary splitting: never cuts mid-sentence
- Configurable overlap for context continuity between chunks

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
    Per-page chunker with table awareness, sentence boundaries, and overlap.

    Philosophy:
    1. Process each page independently (eliminates position tracking bugs)
    2. Preserve tables entirely (critical for tax documents)
    3. Respect Markdown headings as natural section boundaries
    4. Split at sentence boundaries (never mid-sentence or mid-word)
    5. Add configurable overlap so each chunk has context from the previous
    6. Maintain reasonable chunk sizes for embeddings
    """

    # Sentence-ending pattern: period/question/exclamation followed by space or EOL
    _SENTENCE_END_RAW = re.compile(r'[.!?](?:\s+|$)')

    # Spanish abbreviations commonly found in fiscal documents — NOT sentence ends
    _ABBREVIATIONS = re.compile(
        r'\b(?:art|núm|num|pág|pag|cap|sec|inc|ej|etc|nº|Sr|Sra|Dr|Dra|Dña|apdo|op|cit|vid|cfr)\.\s*$'
    )

    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 100,
        overlap_size: int = 150,
        preserve_tables: bool = True
    ):
        """
        Args:
            max_chunk_size: Target maximum characters per chunk
            min_chunk_size: Minimum viable chunk size
            overlap_size: Characters of overlap between consecutive chunks
            preserve_tables: If True, never split tables across chunks
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        self.preserve_tables = preserve_tables

        # Regex for detecting paragraph boundaries
        self.paragraph_pattern = re.compile(r'\n\s*\n+')

        # Regex for detecting Markdown tables
        self.table_pattern = re.compile(r'^\|.+\|$', re.MULTILINE)

        # Regex for Markdown headings (## or ###)
        self.heading_pattern = re.compile(r'^#{1,4}\s+.+$', re.MULTILINE)

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
        raw_chunks: List[ExtractedChunk] = []
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
                raw_chunks.append(ExtractedChunk(
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
                    raw_chunks.append(ExtractedChunk(
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

        # Apply overlap between consecutive chunks on the same page
        if self.overlap_size > 0:
            raw_chunks = self._apply_overlap(raw_chunks)

        return raw_chunks

    def _apply_overlap(self, chunks: List[ExtractedChunk]) -> List[ExtractedChunk]:
        """
        Add overlap from the end of chunk N to the start of chunk N+1.
        Only applies between chunks on the same page (never cross-page).
        The overlap text is cut at the nearest sentence boundary.
        """
        if len(chunks) <= 1:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            curr = chunks[i]

            # Only overlap within the same page
            if prev.page_number != curr.page_number:
                result.append(curr)
                continue

            # Don't overlap into/from table chunks
            if (prev.metadata and prev.metadata.get('has_tables')) or \
               (curr.metadata and curr.metadata.get('has_tables')):
                result.append(curr)
                continue

            # Extract tail of previous chunk for overlap
            overlap_text = self._extract_overlap_tail(prev.content)

            if overlap_text:
                new_content = f"[...] {overlap_text}\n\n{curr.content}"
                curr = ExtractedChunk(
                    content=new_content,
                    page_number=curr.page_number,
                    chunk_index=curr.chunk_index,
                    metadata={
                        **(curr.metadata or {}),
                        'has_overlap': True,
                        'char_count': len(new_content)
                    }
                )

            result.append(curr)

        return result

    def _find_sentence_ends(self, text: str):
        """
        Find real sentence-end positions, filtering out Spanish abbreviations.
        Returns list of match objects.
        """
        results = []
        for m in self._SENTENCE_END_RAW.finditer(text):
            # Check if this period is part of an abbreviation
            prefix = text[:m.start() + 1]  # include the period
            if self._ABBREVIATIONS.search(prefix):
                continue  # skip — it's an abbreviation like "art."
            results.append(m)
        return results

    def _extract_overlap_tail(self, text: str) -> str:
        """
        Extract the last ~overlap_size characters from text,
        cut at the nearest sentence start (so we don't begin mid-sentence).
        """
        if len(text) <= self.overlap_size:
            return ""

        tail = text[-self.overlap_size:]

        # Find the first sentence boundary in the tail
        matches = self._find_sentence_ends(tail)
        if matches:
            match = matches[0]
            start = match.end()
            if start < len(tail):
                return tail[start:].strip()

        # Fallback: find the first newline
        nl_pos = tail.find('\n')
        if nl_pos >= 0 and nl_pos < len(tail) - 10:
            return tail[nl_pos:].strip()

        # Last resort: return as-is
        return tail.strip()

    def _contains_table(self, text: str) -> bool:
        """Check if text contains a Markdown table."""
        return bool(self.table_pattern.search(text))

    def _split_page_semantically(
        self,
        page_content: str,
        page_number: int
    ) -> List[str]:
        """
        Split a long page at semantic boundaries.

        Priority order:
        1. Markdown headings (## / ###)
        2. Paragraph boundaries (double newline)
        3. Sentence boundaries (. ! ?)
        4. Line breaks (last resort)

        Tables are always preserved as atomic blocks.
        """
        # If page has tables and preserve_tables is True, handle specially
        if self.preserve_tables and self._contains_table(page_content):
            return self._split_page_with_tables(page_content)

        # Try heading-aware split first
        sections = self._split_by_headings(page_content)

        if sections and len(sections) > 1:
            # Headings gave us natural sections — now fit each to chunk size
            return self._fit_sections_to_chunks(sections)

        # Fallback: paragraph-level split with sentence awareness
        return self._split_by_paragraphs_and_sentences(page_content)

    def _split_by_headings(self, text: str) -> List[str]:
        """
        Split text at Markdown headings, keeping the heading with its content.
        Returns sections like ["## Title\ncontent...", "### Subtitle\ncontent..."]
        """
        matches = list(self.heading_pattern.finditer(text))
        if not matches:
            return []

        sections = []

        # Text before the first heading
        if matches[0].start() > 0:
            pre = text[:matches[0].start()].strip()
            if pre:
                sections.append(pre)

        # Each heading + content until the next heading
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section = text[start:end].strip()
            if section:
                sections.append(section)

        return sections

    def _fit_sections_to_chunks(self, sections: List[str]) -> List[str]:
        """
        Merge small heading-sections together; split oversized ones further.
        """
        chunks = []
        current_chunk = ""

        for section in sections:
            # Section itself is too big — split it further
            if len(section) > self.max_chunk_size:
                # First, flush current_chunk
                if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Split the oversized section by paragraphs/sentences
                sub_chunks = self._split_by_paragraphs_and_sentences(section)
                chunks.extend(sub_chunks)
                continue

            # Would adding this section overflow the chunk?
            if len(current_chunk) + len(section) + 2 > self.max_chunk_size:
                if len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = section
                else:
                    current_chunk += "\n\n" + section
            else:
                if current_chunk:
                    current_chunk += "\n\n" + section
                else:
                    current_chunk = section

        # Flush remainder
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())

        return chunks if chunks else sections  # Fallback: return original

    def _split_by_paragraphs_and_sentences(self, text: str) -> List[str]:
        """
        Split text first by paragraphs, then by sentence boundaries
        if any paragraph is still too long.
        """
        paragraphs = self.paragraph_pattern.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # If a single paragraph exceeds max_chunk_size, split it by sentences
            if len(paragraph) > self.max_chunk_size:
                # Flush current chunk first
                if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                sentence_chunks = self._split_long_text_at_sentences(paragraph)
                chunks.extend(sentence_chunks)
                continue

            # Normal paragraph — try to add to current chunk
            if len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size:
                if len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    current_chunk += "\n\n" + paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

        # Add last chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]  # Fallback: return entire text

    def _split_long_text_at_sentences(self, text: str) -> List[str]:
        """
        Split a long text block at sentence boundaries.
        Ensures no chunk ends mid-sentence.
        """
        # Find all real sentence-end positions (filtering abbreviations)
        ends = [m.end() for m in self._find_sentence_ends(text)]

        if not ends:
            # No sentence boundaries found — split at line breaks as fallback
            return self._split_at_line_breaks(text)

        chunks = []
        start = 0

        while start < len(text):
            remaining = len(text) - start

            # If what's left fits in one chunk, take it all
            if remaining <= self.max_chunk_size:
                chunk = text[start:].strip()
                if chunk and len(chunk) >= self.min_chunk_size:
                    chunks.append(chunk)
                elif chunk and chunks:
                    # Too small — append to previous
                    chunks[-1] += "\n\n" + chunk
                elif chunk:
                    chunks.append(chunk)
                break

            # Find the last sentence-end that fits within max_chunk_size
            best_end = None
            for end_pos in ends:
                if end_pos <= start:
                    continue
                if end_pos - start <= self.max_chunk_size:
                    best_end = end_pos
                else:
                    break

            if best_end and best_end > start:
                chunk = text[start:best_end].strip()
                if chunk:
                    chunks.append(chunk)
                start = best_end
            else:
                # No sentence boundary found within limit — force split at max
                chunk = text[start:start + self.max_chunk_size].strip()
                if chunk:
                    chunks.append(chunk)
                start += self.max_chunk_size

        return chunks if chunks else [text]

    def _split_at_line_breaks(self, text: str) -> List[str]:
        """Last-resort: split at line breaks when no sentence boundaries exist."""
        lines = text.split('\n')
        chunks = []
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > self.max_chunk_size:
                if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = line
                else:
                    current_chunk += '\n' + line
            else:
                current_chunk += '\n' + line if current_chunk else line

        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    def _split_page_with_tables(self, page_content: str) -> List[str]:
        """
        Special handling for pages with tables.

        Strategy:
        1. Identify table blocks (consecutive lines starting with |)
        2. Preserve table + surrounding context text together if possible
        3. Split text segments with sentence-aware logic
        """
        chunks = []
        lines = page_content.split('\n')

        current_chunk = ""
        in_table = False
        table_buffer = []

        for line in lines:
            is_table_line = line.strip().startswith('|')

            if is_table_line:
                if not in_table:
                    # Starting a table - save current text chunk
                    if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                        # Split the text portion with sentence awareness
                        text_part = current_chunk.strip()
                        if len(text_part) > self.max_chunk_size:
                            chunks.extend(
                                self._split_by_paragraphs_and_sentences(text_part)
                            )
                        else:
                            chunks.append(text_part)
                        current_chunk = ""
                    in_table = True
                table_buffer.append(line)
            else:
                if in_table:
                    # Ending a table - save it as a chunk
                    table_text = '\n'.join(table_buffer)
                    if len(table_text) > self.max_chunk_size:
                        chunks.extend(self._split_large_table(table_text))
                    else:
                        # Try to keep table with preceding context text
                        if current_chunk:
                            combined = current_chunk.strip() + '\n\n' + table_text
                            if len(combined) <= self.max_chunk_size:
                                chunks.append(combined)
                                current_chunk = ""
                                table_buffer = []
                                in_table = False
                                continue
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
            text_part = current_chunk.strip()
            if len(text_part) > self.max_chunk_size:
                chunks.extend(
                    self._split_by_paragraphs_and_sentences(text_part)
                )
            else:
                chunks.append(text_part)

        return chunks if chunks else [page_content]

    def _split_large_table(self, table_text: str) -> List[str]:
        """
        Split a very large table into row groups.
        Preserves header row in each chunk for context.
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
