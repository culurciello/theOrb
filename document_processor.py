import PyPDF2
import docx
import markdown
from typing import List, Dict, Any
import re
import numpy as np
import torch
import clip
from transformers import pipeline
from pathlib import Path
import mimetypes
from sentence_transformers import SentenceTransformer

# Import the new pipeline system
from pipelines.document_processor import DocumentProcessor as PipelineProcessor

class DocumentProcessor:
    def __init__(self):
        """Initialize the document processor using the new pipeline system."""
        # Initialize the pipeline processor with lazy loading
        self._pipeline_processor = None
        
        # Keep backward compatibility - lazy load models for legacy methods
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._clip_model = None
        self._clip_preprocess = None
        self._summarizer = None
        self._sentence_model = None
        
        self.content_categories = [
            "work", "personal", "general info", "contacts info", 
            "conversations", "meetings", "notes"
        ]
        
        self.supported_extensions = {
            'text': ['.txt', '.md', '.markdown', '.pdf', '.doc', '.docx'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'],
            'database': ['.db', '.sqlite', '.sqlite3'],
            'table': ['.csv', '.xlsx', '.xls']
        }

    @property
    def pipeline_processor(self):
        """Lazy load the pipeline processor."""
        if self._pipeline_processor is None:
            print("Loading pipeline processor...")
            self._pipeline_processor = PipelineProcessor()
        return self._pipeline_processor

    @property
    def clip_model(self):
        """Lazy load the CLIP model."""
        if self._clip_model is None:
            print("Loading CLIP model...")
            self._clip_model, self._clip_preprocess = clip.load("ViT-B/32", device=self.device)
        return self._clip_model
    
    @property
    def clip_preprocess(self):
        """Lazy load the CLIP preprocessor."""
        if self._clip_preprocess is None:
            print("Loading CLIP model...")
            self._clip_model, self._clip_preprocess = clip.load("ViT-B/32", device=self.device)
        return self._clip_preprocess

    @property
    def summarizer(self):
        """Lazy load the summarizer model."""
        if self._summarizer is None:
            print("Loading BART summarizer...")
            self._summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        return self._summarizer

    @property
    def sentence_model(self):
        """Lazy load the sentence transformer model."""
        if self._sentence_model is None:
            print("Loading sentence transformer...")
            self._sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._sentence_model

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process an entire directory using the new pipeline system."""
        return self.pipeline_processor.process_directory(directory_path)
    
    def process_single_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single file using the new pipeline system."""
        result = self.pipeline_processor.process_file(file_path)
        
        # Transform the result to match the expected format for backward compatibility
        if result and 'error' not in result:
            # Add MIME type for backward compatibility
            if not file_path.startswith(('http://', 'https://')):
                mime_type, _ = mimetypes.guess_type(file_path)
                result['mime_type'] = mime_type
            
            # Map new pipeline output to old format structure
            if result.get('file_type') == 'text':
                # Text pipeline output: [link, category, summary, embedding_list]
                return self._format_text_output(result)
            elif result.get('file_type') == 'image':
                # Image pipeline output: [link, caption]
                return self._format_image_output(result)
            elif result.get('file_type') == 'table':
                # Table pipeline output: [link, JSON]
                return self._format_table_output(result)
            elif result.get('file_type') == 'multimodal_text':
                # Multimodal text output: [link, category, summary, embedding_list, image_list, tables_list]
                return self._format_multimodal_text_output(result)
            elif result.get('file_type') == 'video':
                # Video pipeline output: [link, key_frames_list, caption_list]
                return self._format_video_output(result)
            elif result.get('file_type') == 'multimodal_webpage':
                # Webpage output: like multimodal text + videos
                return self._format_webpage_output(result)
        
        return result
    
    def _format_text_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format text pipeline output for backward compatibility."""
        # The pipeline returns 'chunks' not 'text_chunks'
        chunks = result.get('chunks', [])
        return {
            'file_path': result['link_to_original_file'],
            'file_type': 'text',
            'content': ' '.join(chunks) if chunks else result.get('summary', ''),
            'summary': result['summary'],
            'chunks': chunks,
            'categories': result['category'],
            'embedding_list': result['embedding_list'],
            'metadata': result.get('metadata', {}),
            'mime_type': result.get('mime_type')
        }
    
    def _format_image_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format image pipeline output for backward compatibility."""
        return {
            'file_path': result['link_to_original_file'],
            'file_type': 'image',
            'content': result['caption'],
            'summary': result['caption'],
            'chunks': [result['caption']],
            'categories': ['image'],
            'clip_embedding': result.get('clip_embedding'),
            'embedding_list': result['embedding_list'],
            'metadata': result.get('metadata', {}),
            'mime_type': result.get('mime_type')
        }
    
    def _format_table_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format table pipeline output for backward compatibility."""
        return {
            'file_path': result['link_to_original_file'],
            'file_type': 'table',
            'content': result['summary'],
            'summary': result['summary'],
            'chunks': [result['summary']],
            'categories': ['table'],
            'json_data': result['json_data'],
            'embedding_list': result['embedding_list'],
            'metadata': result.get('metadata', {}),
            'mime_type': result.get('mime_type')
        }
    
    def _format_multimodal_text_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format multimodal text pipeline output for backward compatibility."""
        chunks = result.get('chunks', [])
        return {
            'file_path': result['link_to_original_file'],
            'file_type': 'multimodal_text',
            'content': result.get('content', ''),
            'summary': result['summary'],
            'chunks': chunks,
            'categories': result['category'],
            'embedding_list': result['embedding_list'],
            'image_list': result.get('image_list', []),
            'tables_list': result.get('tables_list', []),
            'metadata': result.get('metadata', {}),
            'mime_type': result.get('mime_type')
        }
    
    def _format_video_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format video pipeline output for backward compatibility."""
        return {
            'file_path': result['link_to_original_file'],
            'file_type': 'video',
            'content': self._combine_video_captions(result),
            'summary': self._combine_video_captions(result),
            'chunks': [self._combine_video_captions(result)],
            'categories': ['video'],
            'key_frames_v1': result.get('key_frames_v1', {}),
            'key_frames_v2': result.get('key_frames_v2', {}),
            'caption_list_v1': result.get('caption_list_v1', []),
            'caption_list_v2': result.get('caption_list_v2', []),
            'embedding_list_v1': result.get('embedding_list_v1', []),
            'embedding_list_v2': result.get('embedding_list_v2', []),
            'metadata': result.get('metadata', {}),
            'mime_type': result.get('mime_type')
        }
    
    def _format_webpage_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format webpage pipeline output for backward compatibility."""
        chunks = result.get('chunks', [])
        return {
            'file_path': result['link_to_original_file'],
            'file_type': 'multimodal_webpage',
            'content': result.get('content', ''),
            'summary': result['summary'],
            'chunks': chunks,
            'categories': result['category'],
            'embedding_list': result['embedding_list'],
            'image_list': result.get('image_list', []),
            'video_list': result.get('video_list', []),
            'metadata': result.get('metadata', {}),
            'mime_type': result.get('mime_type')
        }
    
    def _combine_video_captions(self, result: Dict[str, Any]) -> str:
        """Combine video captions into a single content string."""
        captions_v1 = [item['caption'] for item in result.get('caption_list_v1', [])]
        captions_v2 = [item['caption'] for item in result.get('caption_list_v2', [])]
        
        all_captions = captions_v1 + captions_v2
        return '. '.join(all_captions) if all_captions else f"Video: {Path(result['link_to_original_file']).stem}"

    # Legacy methods for backward compatibility
    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """Extract CLIP embedding from an image."""
        return self.pipeline_processor.image_pipeline.get_image_embedding(image_path)
    
    def get_image_description(self, image_path: str) -> str:
        """Generate a text description for an image using CLIP."""
        return self.pipeline_processor.image_pipeline.generate_caption(image_path)

    def get_text_embedding_for_image_search(self, text: str) -> np.ndarray:
        """Extract CLIP text embedding for image search."""
        try:
            text_tokens = clip.tokenize([text]).to(self.device)
            
            with torch.no_grad():
                text_features = self.clip_model.encode_text(text_tokens)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
            return text_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Error extracting text embedding: {e}")
            return None
    
    def _determine_file_type(self, file_ext: str) -> str:
        """Determine the file type based on extension."""
        return self.pipeline_processor._determine_file_type(file_ext)
    
    def _categorize_content(self, content: str) -> List[str]:
        """Categorize content using keyword matching."""
        return self.pipeline_processor.text_pipeline.categorize_content(content)
    
    def _generate_summary(self, text: str) -> str:
        """Generate a summary of the text."""
        return self.pipeline_processor.text_pipeline.generate_summary(text)
    
    @staticmethod
    def extract_text_from_file(file_path: str, file_type: str) -> str:
        """Extract text content from various file types."""
        try:
            if file_type.lower() == 'pdf':
                return DocumentProcessor._extract_from_pdf(file_path)
            elif file_type.lower() in ['doc', 'docx']:
                return DocumentProcessor._extract_from_docx(file_path)
            elif file_type.lower() == 'txt':
                return DocumentProcessor._extract_from_txt(file_path)
            elif file_type.lower() in ['md', 'markdown']:
                return DocumentProcessor._extract_from_markdown(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Error processing {file_type} file: {str(e)}")

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()

    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        """Extract text from DOCX file."""
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()

    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """Extract text from TXT file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    @staticmethod
    def _extract_from_markdown(file_path: str) -> str:
        """Extract text from Markdown file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            md_content = file.read()
            html = markdown.markdown(md_content)
            text = re.sub('<.*?>', '', html)
            return text.strip()

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks for better retrieval."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            chunk = text[start:end]
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            
            break_point = max(last_period, last_newline)
            
            if break_point > start + chunk_size // 2:
                end = start + break_point + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return [chunk for chunk in chunks if chunk.strip()]