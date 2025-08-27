from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer

class BasePipeline(ABC):
    """Base class for all document processing pipelines."""
    
    DOCUMENT_CATEGORIES = [
        "work", "personal", "general info", "contacts info", 
        "conversations", "meetings", "notes"
    ]
    
    def __init__(self):
        self._sentence_model = None
    
    @property
    def sentence_model(self):
        """Lazy load the sentence transformer model."""
        if self._sentence_model is None:
            print("Loading SentenceTransformer for pipeline...")
            self._sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._sentence_model
    
    @abstractmethod
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process a file and return structured data for database storage."""
        pass
    
    def get_sentence_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """Generate sentence embeddings for text chunks."""
        try:
            embeddings = self.sentence_model.encode(text_chunks)
            return embeddings.tolist()
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []
    
    def categorize_content(self, content: str) -> List[str]:
        """Categorize content using keyword matching."""
        content_lower = content.lower()
        assigned_categories = []
        
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
        
        if not assigned_categories:
            assigned_categories.append('general info')
        
        return assigned_categories
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks."""
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