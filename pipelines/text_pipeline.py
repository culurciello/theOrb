from typing import Dict, Any, List
from pathlib import Path
import PyPDF2
# import docx  # DISABLED: docx functionality commented out (no .docx files in use)
import markdown
import re
import torch
import mimetypes
from transformers import pipeline
from .base_pipeline import BasePipeline
from .chunk import HierarchicalChunker

class TextPipeline(BasePipeline):
    """
    Text processing pipeline:
    - break into chunks --> sentence embeddings --> create list
    - send first 1000 words --> get summary, get category
    - send to database: [link to original file, category, summary, embedding list]
    """

    def __init__(self):
        super().__init__()
        self._summarizer = None
        self._summarizer_device = None
        self._cuda_failed = False
        # Initialize hierarchical chunker with 500 token chunks and 2 sentence overlap
        self.hierarchical_chunker = HierarchicalChunker(chunk_tokens=500, overlap_sentences=2)

    def _read_text_file_with_encoding_detection(self, file_path: Path) -> str:
        """
        Read text file with automatic encoding detection.
        Tries multiple encodings and falls back to UTF-8 with error replacement.
        """
        # Try multiple encodings in order of preference
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read().strip()
                    if content:
                        print(f"\033[92m✓ Successfully read {file_path} with {encoding} encoding\033[0m")
                        return content
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        # If all encodings fail, try binary mode and decode with errors='replace'
        try:
            with open(file_path, 'rb') as file:
                raw_content = file.read()
                content = raw_content.decode('utf-8', errors='replace').strip()
                print(f"\033[93m⚠️  Using UTF-8 with character replacement for {file_path}\033[0m")
                return content
        except Exception as e:
            raise Exception(f"Could not read text file {file_path} with any encoding: {str(e)}")
    
    def _clear_cuda_cache(self):
        """Clear CUDA cache and reset device."""
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            except Exception as e:
                print(f"Warning: Could not clear CUDA cache: {e}")

    @property
    def summarizer(self):
        """Lazy load the summarizer model with proper device handling."""
        if self._summarizer is None:
            try:
                # Determine device to use
                if self._cuda_failed:
                    # CUDA previously failed, use CPU
                    device = -1  # CPU
                    device_name = "CPU"
                    print("⚠️  Using CPU for BART summarizer (CUDA previously failed)")
                elif torch.cuda.is_available():
                    device = 0  # First CUDA device
                    device_name = f"cuda:{device}"
                    print(f"Loading BART summarizer on {device_name}...")
                else:
                    device = -1  # CPU
                    device_name = "CPU"
                    print("Loading BART summarizer on CPU (no CUDA available)...")

                # Load model with explicit device
                self._summarizer = pipeline(
                    "summarization",
                    model="facebook/bart-large-cnn",
                    device=device
                )
                self._summarizer_device = device_name
                print(f"✓ BART summarizer loaded successfully on {device_name}")

            except Exception as e:
                print(f"❌ Error loading BART summarizer: {e}")
                # Clear CUDA cache in case of error
                self._clear_cuda_cache()

                # Try CPU fallback if CUDA failed
                if device != -1:
                    print("🔄 Attempting CPU fallback...")
                    try:
                        self._summarizer = pipeline(
                            "summarization",
                            model="facebook/bart-large-cnn",
                            device=-1
                        )
                        self._summarizer_device = "CPU"
                        self._cuda_failed = True
                        print("✓ BART summarizer loaded on CPU (fallback)")
                    except Exception as cpu_error:
                        print(f"❌ CPU fallback also failed: {cpu_error}")
                        raise RuntimeError(f"Failed to load BART summarizer on both GPU and CPU: {e}")
                else:
                    raise RuntimeError(f"Failed to load BART summarizer: {e}")

        return self._summarizer
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process text file according to the pipeline specification."""
        file_path = Path(file_path)

        # Extract text content
        content = self.extract_text_from_file(str(file_path))

        # Break into chunks using hierarchical layout-aware chunking
        chunks = self.hierarchical_chunker.chunk_text(content)

        # Generate sentence embeddings for chunks using optimized batching
        embedding_list = self.get_sentence_embeddings(chunks)
        
        # Get first 1000 words for summary and categorization
        words = content.split()[:1000]
        first_1000_words = ' '.join(words)
        
        # Generate summary
        summary = self.generate_summary(first_1000_words)
        
        # Get category
        category = self.categorize_content(first_1000_words)

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return {
            'link_to_original_file': str(file_path),
            'categories': category,  # Keep as 'categories' for consistency with routes.py
            'summary': summary,
            'embedding_list': embedding_list,
            'chunks': chunks,
            'content': content,  # Full text content for storage
            'file_type': 'text',
            'mime_type': mime_type,
            'metadata': {
                'word_count': len(content.split()),
                'chunk_count': len(chunks),
                'file_extension': file_path.suffix
            }
        }
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text content from various file types."""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext in ['.doc', '.docx']:
                # DISABLED: docx functionality commented out
                raise ValueError(f"Word document processing disabled: {file_ext}")
                # return self._extract_from_docx(file_path)
            elif file_ext == '.txt':
                return self._extract_from_txt(file_path)
            elif file_ext in ['.md', '.markdown']:
                return self._extract_from_markdown(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
        except Exception as e:
            raise Exception(f"Error processing {file_ext} file: {str(e)}")
    
    def generate_summary(self, text: str) -> str:
        """Generate summary from first 1000 words with robust error handling."""
        try:
            # Validate input
            if not text or len(text.strip()) < 50:
                return text[:200] if text else ""

            # Truncate to avoid BART's max token limit
            # BART max tokens = 1024, but we'll be conservative and use ~500 words (~700 tokens)
            words = text.split()
            if len(words) > 500:
                truncated_text = ' '.join(words[:500])
            else:
                truncated_text = text

            # Clean and validate truncated text
            truncated_text = truncated_text.strip()
            if len(truncated_text) < 100:
                return truncated_text

            # Additional validation: ensure text isn't too long in characters
            # BART tokenizer can have issues with very long strings
            if len(truncated_text) > 3000:
                truncated_text = truncated_text[:3000]

            # Try summarization with CUDA error handling
            try:
                summary = self.summarizer(
                    truncated_text,
                    max_length=150,
                    min_length=30,
                    do_sample=False,
                    truncation=True  # Explicitly enable truncation
                )

                # Handle empty summary result
                if summary and len(summary) > 0 and 'summary_text' in summary[0]:
                    return summary[0]['summary_text']
                else:
                    # Fallback to first few sentences
                    sentences = truncated_text.split('.')[:3]
                    return '. '.join(sentences) + '.' if sentences else truncated_text[:200]

            except RuntimeError as cuda_error:
                error_msg = str(cuda_error).lower()

                # Check if it's a CUDA error
                if 'cuda' in error_msg or 'device' in error_msg:
                    print(f"❌ CUDA error during summarization: {cuda_error}")
                    print("🔄 Clearing CUDA cache and attempting CPU fallback...")

                    # Clear CUDA cache
                    self._clear_cuda_cache()

                    # Mark CUDA as failed
                    self._cuda_failed = True

                    # Reset summarizer to force CPU reload
                    self._summarizer = None

                    # Try again with CPU
                    try:
                        print("🔄 Retrying summarization on CPU...")
                        summary = self.summarizer(
                            truncated_text,
                            max_length=150,
                            min_length=30,
                            do_sample=False,
                            truncation=True
                        )

                        if summary and len(summary) > 0 and 'summary_text' in summary[0]:
                            return summary[0]['summary_text']
                    except Exception as retry_error:
                        print(f"❌ CPU retry also failed: {retry_error}")
                        # Fall through to fallback

                # Fallback for any error
                sentences = truncated_text.split('.')[:3]
                fallback = '. '.join(sentences) + '.' if sentences else truncated_text[:200]
                return fallback

        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            # Better fallback - return first few sentences instead of raw text
            try:
                sentences = text.split('.')[:2]
                fallback = '. '.join(sentences) + '.' if sentences else text[:200]
                return fallback + "..." if len(fallback) < len(text) else fallback
            except:
                # Ultimate fallback
                return text[:200] if text else "Summary unavailable"
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()

    # DISABLED: docx functionality commented out
    # def _extract_from_docx(self, file_path: Path) -> str:
    #     """Extract text from DOCX file."""
    #     doc = docx.Document(file_path)
    #     text = ""
    #     for paragraph in doc.paragraphs:
    #         text += paragraph.text + "\n"
    #     return text.strip()

    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file with automatic encoding detection."""
        return self._read_text_file_with_encoding_detection(file_path)

    def _extract_from_markdown(self, file_path: Path) -> str:
        """Extract text from Markdown file with automatic encoding detection."""
        md_content = self._read_text_file_with_encoding_detection(file_path)
        html = markdown.markdown(md_content)
        text = re.sub('<.*?>', '', html)
        return text.strip()