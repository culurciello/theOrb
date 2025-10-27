"""
Layout-aware hierarchical chunking for document processing.

Architecture:
1. Structure Detection: Detects markdown, numbers, all caps headers, underlined headers
2. Boundary Aware Splitting: Preserves semantic units by not splitting across headers
3. Division: Smart splitting based on token limits (paragraphs → sentences)
4. Grouping: Groups content until token limit, with overlap
5. Context Enrichment: Prepends hierarchical path to each chunk
"""

from typing import List, Dict, Tuple, Optional
import re


class Section:
    """Represents a document section with hierarchical structure."""

    def __init__(self, type: str, level: int, title: str, start_line: int):
        self.type = type  # 'markdown', 'numbered', 'allcaps', 'underlined'
        self.level = level
        self.title = title
        self.start_line = start_line

    def __repr__(self):
        return f"Section(type={self.type}, level={self.level}, title='{self.title}', line={self.start_line})"


class HierarchicalChunker:
    """
    Layout-aware hierarchical document chunker.

    Implements a multi-stage chunking strategy:
    1. Detect document structure (headers at various levels)
    2. Extract sections between headers
    3. Split large sections intelligently (paragraphs → sentences)
    4. Group content with overlap
    5. Enrich chunks with hierarchical context
    """

    def __init__(self, chunk_tokens: int = 500, overlap_sentences: int = 2):
        """
        Initialize the hierarchical chunker.

        Args:
            chunk_tokens: Target token count per chunk (default 500)
            overlap_sentences: Number of sentences to overlap between chunks (default 2)
        """
        self.chunk_tokens = chunk_tokens
        self.overlap_sentences = overlap_sentences

        # Approximate token to word ratio (1 token ≈ 0.75 words)
        self.token_to_word_ratio = 0.75
        self.chunk_words = int(chunk_tokens * self.token_to_word_ratio)

    def chunk_text(self, text: str) -> List[str]:
        """
        Main entry point for chunking text.

        Args:
            text: Document text to chunk

        Returns:
            List of text chunks with hierarchical context
        """
        if not text.strip():
            return []

        # Step 1: Detect document structure
        lines = text.split('\n')
        sections = self._detect_structure(lines)

        # Step 2: Extract content sections
        section_contents = self._extract_sections(lines, sections)

        # Step 3 & 4: Process sections and create chunks
        chunks = []
        for section_info, content in section_contents:
            section_chunks = self._process_section(content, section_info)
            chunks.extend(section_chunks)

        # If no sections were detected, treat entire document as one section
        if not chunks:
            chunks = self._process_section(text, None)

        return chunks

    def _detect_structure(self, lines: List[str]) -> List[Section]:
        """
        Detect document structure by identifying headers.

        Detects:
        - Markdown headers (# Header)
        - Numbered headers (1. Header, 1.1 Header)
        - All caps headers (HEADER TEXT)
        - Underlined headers (Header\n====)

        Args:
            lines: Document lines

        Returns:
            List of detected sections
        """
        sections = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # 1. Markdown headers (# Header)
            markdown_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if markdown_match:
                level = len(markdown_match.group(1))
                title = markdown_match.group(2).strip()
                sections.append(Section('markdown', level, title, i))
                i += 1
                continue

            # 2. Numbered headers (1. Header, 1.1 Header, 1.1.1 Header)
            numbered_match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)$', line)
            if numbered_match:
                number = numbered_match.group(1)
                title = numbered_match.group(2).strip()
                level = number.count('.') + 1
                sections.append(Section('numbered', level, title, i))
                i += 1
                continue

            # 3. Underlined headers (Header\n==== or Header\n----)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Check for === underline (level 1)
                if re.match(r'^={3,}$', next_line):
                    sections.append(Section('underlined', 1, line, i))
                    i += 2
                    continue
                # Check for --- underline (level 2)
                if re.match(r'^-{3,}$', next_line):
                    sections.append(Section('underlined', 2, line, i))
                    i += 2
                    continue

            # 4. All caps headers (must be relatively short and all uppercase)
            if (len(line) > 3 and len(line) < 100 and
                line.isupper() and
                not re.match(r'^[\d\s\W]+$', line)):  # Not just numbers/punctuation
                sections.append(Section('allcaps', 3, line, i))
                i += 1
                continue

            i += 1

        return sections

    def _extract_sections(self, lines: List[str], sections: List[Section]) -> List[Tuple[Optional[Section], str]]:
        """
        Extract content between section boundaries.

        Args:
            lines: Document lines
            sections: Detected sections

        Returns:
            List of (section_info, content) tuples
        """
        if not sections:
            return [(None, '\n'.join(lines))]

        section_contents = []

        for i, section in enumerate(sections):
            # Determine content range
            # For underlined headers, skip both the title and underline
            start = section.start_line + 1
            if section.type == 'underlined':
                start += 1  # Skip the underline as well

            end = sections[i + 1].start_line if i + 1 < len(sections) else len(lines)

            # Extract content (skip the header line itself)
            content_lines = lines[start:end]
            content = '\n'.join(content_lines).strip()

            if content:
                section_contents.append((section, content))

        return section_contents

    def _process_section(self, content: str, section_info: Optional[Section]) -> List[str]:
        """
        Process a section with boundary-aware splitting.

        Division logic:
        - text <= 500 tokens → keep entire thing
        - text > 500 tokens → split by paragraphs (double newlines)
        - paragraph > 500 tokens → split by sentences

        Args:
            content: Section content
            section_info: Section metadata (or None for root)

        Returns:
            List of chunks with hierarchical context
        """
        if not content.strip():
            return []

        # Check token count
        word_count = len(content.split())

        # If content fits in one chunk, return it
        if word_count <= self.chunk_words:
            return [self._enrich_with_context(content, section_info)]

        # Split by paragraphs (double newlines)
        paragraphs = re.split(r'\n\s*\n', content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk_parts = []
        current_word_count = 0
        overlap_buffer = []  # Store last n sentences for overlap

        for paragraph in paragraphs:
            para_word_count = len(paragraph.split())

            # If single paragraph exceeds limit, split by sentences
            if para_word_count > self.chunk_words:
                # Save current chunk if it has content
                if current_chunk_parts:
                    chunk_text = '\n\n'.join(current_chunk_parts)
                    chunks.append(self._enrich_with_context(chunk_text, section_info))
                    # Store overlap
                    overlap_buffer = self._extract_last_sentences(chunk_text, self.overlap_sentences)
                    current_chunk_parts = []
                    current_word_count = 0

                # Split large paragraph by sentences
                sentence_chunks = self._split_by_sentences(paragraph, section_info, overlap_buffer)
                chunks.extend(sentence_chunks)

                # Update overlap buffer with last chunk's sentences
                if sentence_chunks:
                    overlap_buffer = self._extract_last_sentences(
                        self._remove_context(sentence_chunks[-1], section_info),
                        self.overlap_sentences
                    )

                continue

            # Check if adding this paragraph would exceed limit
            if current_word_count + para_word_count > self.chunk_words and current_chunk_parts:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk_parts)
                chunks.append(self._enrich_with_context(chunk_text, section_info))

                # Store overlap sentences
                overlap_buffer = self._extract_last_sentences(chunk_text, self.overlap_sentences)

                # Start new chunk with overlap
                if overlap_buffer:
                    current_chunk_parts = [' '.join(overlap_buffer)]
                    current_word_count = sum(len(s.split()) for s in overlap_buffer)
                else:
                    current_chunk_parts = []
                    current_word_count = 0

            # Add paragraph to current chunk
            current_chunk_parts.append(paragraph)
            current_word_count += para_word_count

        # Add final chunk if it has content
        if current_chunk_parts:
            chunk_text = '\n\n'.join(current_chunk_parts)
            chunks.append(self._enrich_with_context(chunk_text, section_info))

        return chunks

    def _split_by_sentences(self, text: str, section_info: Optional[Section],
                           overlap_buffer: List[str]) -> List[str]:
        """
        Split text by sentence boundaries with overlap.

        Args:
            text: Text to split
            section_info: Section metadata
            overlap_buffer: Previous sentences to overlap

        Returns:
            List of chunks
        """
        # Split by sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_sentences = list(overlap_buffer) if overlap_buffer else []
        current_word_count = sum(len(s.split()) for s in current_sentences)

        for sentence in sentences:
            sentence_word_count = len(sentence.split())

            # Check if adding this sentence would exceed limit
            if current_word_count + sentence_word_count > self.chunk_words and current_sentences:
                # Save current chunk
                chunk_text = ' '.join(current_sentences)
                chunks.append(self._enrich_with_context(chunk_text, section_info))

                # Start new chunk with overlap
                overlap = current_sentences[-self.overlap_sentences:] if len(current_sentences) > self.overlap_sentences else current_sentences
                current_sentences = list(overlap)
                current_word_count = sum(len(s.split()) for s in current_sentences)

            # Add sentence to current chunk
            current_sentences.append(sentence)
            current_word_count += sentence_word_count

        # Add final chunk
        if current_sentences:
            chunk_text = ' '.join(current_sentences)
            chunks.append(self._enrich_with_context(chunk_text, section_info))

        return chunks

    def _extract_last_sentences(self, text: str, n: int) -> List[str]:
        """Extract last n sentences from text for overlap."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences[-n:] if len(sentences) > n else sentences

    def _enrich_with_context(self, text: str, section_info: Optional[Section]) -> str:
        """
        Prepend hierarchical context to chunk.

        Args:
            text: Chunk text
            section_info: Section metadata

        Returns:
            Enriched chunk with context
        """
        if not section_info:
            return text

        # Build hierarchical path
        context = f"[{section_info.title}]\n\n"

        return context + text

    def _remove_context(self, chunk: str, section_info: Optional[Section]) -> str:
        """Remove context prefix from chunk (for overlap extraction)."""
        if not section_info:
            return chunk

        # Remove context line
        lines = chunk.split('\n')
        if lines and lines[0].startswith('[') and lines[0].endswith(']'):
            return '\n'.join(lines[2:])  # Skip context line and blank line

        return chunk


# Convenience function for backward compatibility
def chunk_text_hierarchical(text: str, chunk_tokens: int = 500, overlap_sentences: int = 2) -> List[str]:
    """
    Chunk text using hierarchical layout-aware strategy.

    Args:
        text: Text to chunk
        chunk_tokens: Target tokens per chunk
        overlap_sentences: Sentences to overlap between chunks

    Returns:
        List of chunks
    """
    chunker = HierarchicalChunker(chunk_tokens=chunk_tokens, overlap_sentences=overlap_sentences)
    return chunker.chunk_text(text)
