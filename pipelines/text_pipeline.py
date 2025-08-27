from typing import Dict, Any, List
from pathlib import Path
import PyPDF2
import docx
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
        
        # Break into chunks
        chunks = self.chunk_text(content)
        
        # Generate sentence embeddings for chunks
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
                return self._extract_from_docx(file_path)
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

    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()

    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    def _extract_from_markdown(self, file_path: Path) -> str:
        """Extract text from Markdown file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            md_content = file.read()
            html = markdown.markdown(md_content)
            text = re.sub('<.*?>', '', html)
            return text.strip()