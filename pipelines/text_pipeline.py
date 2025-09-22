from typing import Dict, Any, List
from pathlib import Path
import PyPDF2
# import docx  # DISABLED: docx functionality commented out (no .docx files in use)
import markdown
import re
from transformers import pipeline
from .base_pipeline import BasePipeline

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
    
    @property
    def summarizer(self):
        """Lazy load the summarizer model."""
        if self._summarizer is None:
            print("Loading BART summarizer for TextPipeline...")
            self._summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        return self._summarizer
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process text file according to the pipeline specification."""
        file_path = Path(file_path)
        
        # Extract text content
        content = self.extract_text_from_file(str(file_path))
        
        # Break into chunks using smart chunking
        chunks = self.chunk_text_smart(content, chunk_tokens=500, overlap_tokens=50)

        # Generate sentence embeddings for chunks using optimized batching
        embedding_list = self.get_sentence_embeddings(chunks)
        
        # Get first 1000 words for summary and categorization
        words = content.split()[:1000]
        first_1000_words = ' '.join(words)
        
        # Generate summary
        summary = self.generate_summary(first_1000_words)
        
        # Get category
        category = self.categorize_content(first_1000_words)
        
        return {
            'link_to_original_file': str(file_path),
            'category': category,
            'summary': summary,
            'embedding_list': embedding_list,
            'chunks': chunks,
            'file_type': 'text',
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
        """Generate summary from first 1000 words."""
        try:
            if len(text.split()) < 50:
                return text
            
            summary = self.summarizer(text, max_length=150, min_length=50, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            print(f"Error generating summary: {e}")
            return text[:500] + "..."
    
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