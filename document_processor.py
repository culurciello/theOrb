import os
import PyPDF2
import docx
import markdown
from typing import List, Tuple, Dict, Any
import re
import cv2
import numpy as np
from PIL import Image
import torch
import clip
from transformers import pipeline
import ffmpeg
from pathlib import Path
import mimetypes
import sqlite3
import pandas as pd
from sentence_transformers import SentenceTransformer

class DocumentProcessor:
    def __init__(self):
        """Initialize the document processor with required models."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
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
    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process an entire directory and return processed documents."""
        processed_docs = []
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Invalid directory path: {directory_path}")
        
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                try:
                    doc_data = self.process_single_file(str(file_path))
                    if doc_data:
                        processed_docs.append(doc_data)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
        
        return processed_docs
    
    def process_single_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single file and return structured data."""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        file_type = self._determine_file_type(file_ext)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if file_type == 'text':
            result = self._process_text_file(file_path, file_ext)
        elif file_type == 'image':
            result = self._process_image_file(file_path)
        elif file_type == 'video':
            result = self._process_video_file(file_path)
        elif file_type == 'database':
            result = self._process_database_file(file_path)
        elif file_type == 'table':
            result = self._process_table_file(file_path)
        else:
            return None
        
        # Add MIME type to result
        if result:
            result['mime_type'] = mime_type
        
        return result
    
    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """Extract CLIP embedding from an image."""
        try:
            image = Image.open(image_path)
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
            return image_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Error extracting image embedding: {e}")
            return None
    
    def get_image_description(self, image_path: str) -> str:
        """Generate a text description for an image using CLIP."""
        try:
            from PIL import Image
            image = Image.open(image_path)
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            # More descriptive text queries for better captions
            text_queries = [
                "a photo of", "a drawing of", "a diagram of", "a screenshot of", 
                "a document with", "a chart showing", "a graph of", "people in", 
                "a meeting with", "work related content", "a personal photo", 
                "text document", "presentation slide", "data visualization",
                "artwork", "landscape", "indoor scene", "outdoor scene"
            ]
            
            text_tokens = clip.tokenize(text_queries).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                text_features = self.clip_model.encode_text(text_tokens)
                
                similarities = (image_features @ text_features.T).softmax(dim=-1)
                best_match_idx = similarities.argmax().item()
                best_description = text_queries[best_match_idx]
                confidence = float(similarities.max())
                
            # Generate more natural description
            if confidence > 0.3:  # High confidence
                return best_description
            else:
                return "an image"  # Low confidence fallback
                
        except Exception as e:
            print(f"Error generating image description: {e}")
            return "an image"

    def get_text_embedding_for_image_search(self, text: str) -> np.ndarray:
        """Extract CLIP text embedding for image search."""
        try:
            text_tokens = clip.tokenize([text]).to(self.device)
            
            with torch.no_grad():
                text_features = self.clip_model.encode_text(text_tokens)
                # Normalize the features
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
            return text_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Error extracting text embedding: {e}")
            return None
    
    def _determine_file_type(self, file_ext: str) -> str:
        """Determine the file type based on extension."""
        for file_type, extensions in self.supported_extensions.items():
            if file_ext in extensions:
                return file_type
        return 'unknown'
    
    def _process_text_file(self, file_path: Path, file_ext: str) -> Dict[str, Any]:
        """Process text-based files."""
        content = self.extract_text_from_file(str(file_path), file_ext[1:])
        
        # Generate summary from first 1000 words
        words = content.split()[:1000]
        summary_text = ' '.join(words)
        summary = self._generate_summary(summary_text) if len(words) > 50 else summary_text
        
        # Chunk the text
        chunks = self.chunk_text(content)
        
        # Categorize content
        categories = self._categorize_content(content)
        
        return {
            'file_path': str(file_path),
            'file_type': 'text',
            'content': content,
            'summary': summary,
            'chunks': chunks,
            'categories': categories,
            'metadata': {
                'file_size': file_path.stat().st_size,
                'file_extension': file_ext,
                'word_count': len(content.split())
            }
        }
    
    def _process_image_file(self, file_path: Path) -> Dict[str, Any]:
        """Process image files using CLIP."""
        try:
            image = Image.open(file_path)
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            # Generate image description using CLIP
            text_queries = [
                "a photo of", "a diagram of", "a screenshot of", "a document with",
                "a chart showing", "a graph of", "people in", "a meeting with",
                "work related", "personal photo"
            ]
            
            text_tokens = clip.tokenize(text_queries).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                text_features = self.clip_model.encode_text(text_tokens)
                
                # Normalize features for similarity search later
                image_features_normalized = image_features / image_features.norm(dim=-1, keepdim=True)
                
                similarities = (image_features @ text_features.T).softmax(dim=-1)
                best_match_idx = similarities.argmax().item()
                best_description = text_queries[best_match_idx]
            
            # Create text description for processing
            description = f"Image: {best_description} {file_path.stem}"
            
            # Categorize based on description
            categories = self._categorize_content(description)
            categories.insert(0, 'image')
            
            # Chunk the description
            chunks = [description]
            
            return {
                'file_path': str(file_path),
                'file_type': 'image',
                'content': description,
                'summary': description,
                'chunks': chunks,
                'categories': categories,
                'clip_embedding': image_features_normalized.cpu().numpy().flatten().tolist(),
                'metadata': {
                    'file_size': file_path.stat().st_size,
                    'file_extension': file_path.suffix,
                    'image_dimensions': f"{image.width}x{image.height}",
                    'clip_confidence': float(similarities.max())
                }
            }
        except Exception as e:
            print(f"Error processing image {file_path}: {e}")
            return None
    
    def _process_video_file(self, file_path: Path) -> Dict[str, Any]:
        """Process video files by extracting keyframes."""
        try:
            cap = cv2.VideoCapture(str(file_path))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            # Extract keyframes (every 30 seconds or 5 frames max)
            keyframe_interval = max(1, int(fps * 30)) if fps > 0 else 1
            max_keyframes = 5
            keyframes = []
            
            frame_indices = [i * keyframe_interval for i in range(max_keyframes) if i * keyframe_interval < total_frames]
            
            descriptions = []
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    # Convert to PIL Image
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # Process with CLIP
                    image_tensor = self.clip_preprocess(pil_image).unsqueeze(0).to(self.device)
                    
                    text_queries = [
                        "a meeting", "a presentation", "people talking", "a workspace",
                        "a screen recording", "a tutorial", "a conference"
                    ]
                    
                    text_tokens = clip.tokenize(text_queries).to(self.device)
                    
                    with torch.no_grad():
                        image_features = self.clip_model.encode_image(image_tensor)
                        text_features = self.clip_model.encode_text(text_tokens)
                        
                        similarities = (image_features @ text_features.T).softmax(dim=-1)
                        best_match_idx = similarities.argmax().item()
                        best_description = text_queries[best_match_idx]
                    
                    timestamp = frame_idx / fps if fps > 0 else frame_idx
                    descriptions.append(f"At {timestamp:.1f}s: {best_description}")
            
            cap.release()
            
            # Combine descriptions
            content = f"Video: {file_path.stem}. " + ". ".join(descriptions)
            
            # Categorize
            categories = self._categorize_content(content)
            categories.insert(0, 'video')
            
            # Chunk the content
            chunks = [content]
            
            return {
                'file_path': str(file_path),
                'file_type': 'video',
                'content': content,
                'summary': content,
                'chunks': chunks,
                'categories': categories,
                'metadata': {
                    'file_size': file_path.stat().st_size,
                    'file_extension': file_path.suffix,
                    'duration_seconds': duration,
                    'total_frames': total_frames,
                    'fps': fps,
                    'keyframes_extracted': len(descriptions)
                }
            }
        except Exception as e:
            print(f"Error processing video {file_path}: {e}")
            return None
    
    def _process_database_file(self, file_path: Path) -> Dict[str, Any]:
        """Process database files."""
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            content_parts = [f"Database: {file_path.stem}"]
            
            for table_name in tables[:5]:  # Limit to first 5 tables
                table_name = table_name[0]
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                content_parts.append(f"Table {table_name}: {len(rows)} sample rows, columns: {', '.join(columns)}")
            
            conn.close()
            
            content = ". ".join(content_parts)
            categories = self._categorize_content(content)
            categories.insert(0, 'database')
            
            return {
                'file_path': str(file_path),
                'file_type': 'database',
                'content': content,
                'summary': content,
                'chunks': [content],
                'categories': categories,
                'metadata': {
                    'file_size': file_path.stat().st_size,
                    'file_extension': file_path.suffix,
                    'table_count': len(tables)
                }
            }
        except Exception as e:
            print(f"Error processing database {file_path}: {e}")
            return None
    
    def _process_table_file(self, file_path: Path) -> Dict[str, Any]:
        """Process table files (CSV, Excel)."""
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=5)
            else:
                df = pd.read_excel(file_path, nrows=5)
            
            content = f"Table: {file_path.stem}. Columns: {', '.join(df.columns)}. Sample data: {df.to_string(index=False)}"
            
            categories = self._categorize_content(content)
            categories.insert(0, 'table')
            
            return {
                'file_path': str(file_path),
                'file_type': 'table',
                'content': content,
                'summary': content,
                'chunks': [content],
                'categories': categories,
                'metadata': {
                    'file_size': file_path.stat().st_size,
                    'file_extension': file_path.suffix,
                    'columns': list(df.columns),
                    'row_count': len(df)
                }
            }
        except Exception as e:
            print(f"Error processing table {file_path}: {e}")
            return None
    
    def _generate_summary(self, text: str) -> str:
        """Generate a summary of the text."""
        try:
            if len(text.split()) < 50:
                return text
            
            summary = self.summarizer(text, max_length=150, min_length=50, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            print(f"Error generating summary: {e}")
            return text[:500] + "..."
    
    def _categorize_content(self, content: str) -> List[str]:
        """Categorize content using keyword matching and semantic similarity."""
        content_lower = content.lower()
        assigned_categories = []
        
        # Keyword-based categorization
        work_keywords = ['meeting', 'project', 'deadline', 'report', 'presentation', 'office', 'work', 'business', 'company']
        personal_keywords = ['family', 'friend', 'vacation', 'personal', 'home', 'birthday', 'wedding']
        contact_keywords = ['phone', 'email', 'address', 'contact', 'number', '@']
        conversation_keywords = ['chat', 'message', 'conversation', 'talk', 'discussion']
        meeting_keywords = ['meeting', 'conference', 'call', 'zoom', 'teams', 'agenda']
        notes_keywords = ['note', 'memo', 'reminder', 'todo', 'checklist']
        
        if any(keyword in content_lower for keyword in work_keywords):
            assigned_categories.append('work')
        if any(keyword in content_lower for keyword in personal_keywords):
            assigned_categories.append('personal')
        if any(keyword in content_lower for keyword in contact_keywords):
            assigned_categories.append('contacts info')
        if any(keyword in content_lower for keyword in conversation_keywords):
            assigned_categories.append('conversations')
        if any(keyword in content_lower for keyword in meeting_keywords):
            assigned_categories.append('meetings')
        if any(keyword in content_lower for keyword in notes_keywords):
            assigned_categories.append('notes')
        
        # Default to general info if no specific category found
        if not assigned_categories:
            assigned_categories.append('general info')
        
        return assigned_categories
    
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
            # Remove HTML tags to get plain text
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
            
            # Try to break at sentence boundary
            chunk = text[start:end]
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            
            break_point = max(last_period, last_newline)
            
            if break_point > start + chunk_size // 2:
                end = start + break_point + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return [chunk for chunk in chunks if chunk.strip()]