from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

class BasePipeline(ABC):
    """Base class for all document processing pipelines."""
    
    DOCUMENT_CATEGORIES = [
        "work", "personal", "general info", "contacts info", 
        "conversations", "meetings", "notes"
    ]
    
    def __init__(self):
        self._sentence_model = None
        self._cuda_failed = False

        # GPU optimization setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        self.batch_size = self._get_optimal_batch_size()
        print(f"📍 BasePipeline initialized with device: {self.device}")
    
    def _clear_cuda_cache(self):
        """Clear CUDA cache and reset device."""
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                print("✓ CUDA cache cleared")
            except Exception as e:
                print(f"⚠️  Warning: Could not clear CUDA cache: {e}")

    @property
    def sentence_model(self):
        """Lazy load the sentence transformer model."""
        if self._sentence_model is None:
            print("Loading SentenceTransformer for pipeline...")
            self._sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

            # If CUDA previously failed, move model to CPU
            if self._cuda_failed and self.device.type == 'cuda':
                print("⚠️  CUDA previously failed, using CPU for embeddings")
                self.device = torch.device('cpu')

        return self._sentence_model
    
    @abstractmethod
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process a file and return structured data for database storage."""
        pass
    
    def _get_optimal_batch_size(self) -> int:
        """Get optimal batch size based on device capabilities."""
        base_batch_size = 32

        if self.device.type == "cuda":
            # GPU detected - increase batch size significantly
            return min(128, base_batch_size * 2)
        elif self.device.type == "mps":
            # Apple Silicon - moderate increase
            return min(96, base_batch_size + 32)
        else:
            # CPU - keep conservative
            return base_batch_size

    def get_sentence_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """Generate sentence embeddings for text chunks with optimized batching."""
        try:
            embeddings = self.batch_embed_optimized(text_chunks)
            return embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []

    def batch_embed_optimized(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Optimized batch embedding processing with GPU acceleration and error handling.
        Based on kb/ingest.py batch_embed function.
        """
        if not texts:
            return np.array([])

        if batch_size is None:
            batch_size = self.batch_size

        try:
            # For small batches, use simple encoding with error handling
            if len(texts) <= batch_size:
                return self._safe_encode(texts)

            # For large batches, use optimized processing
            embeddings = []
            total_batches = (len(texts) + batch_size - 1) // batch_size

            if total_batches > 1:
                print(f"\033[94m  Processing {len(texts)} texts in {total_batches} batches (batch_size={batch_size})...\033[0m")

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]

                # Use safe encoding for each batch
                batch_embeddings = self._safe_encode(batch)

                if batch_embeddings is not None:
                    if isinstance(batch_embeddings, list):
                        embeddings.extend(batch_embeddings)
                    else:
                        embeddings.append(batch_embeddings)

            # Combine all embeddings
            if embeddings and isinstance(embeddings[0], np.ndarray):
                return np.vstack(embeddings)
            else:
                return np.array(embeddings)

        except Exception as e:
            print(f"Error in batch_embed_optimized: {e}")
            # Fallback to CPU processing
            return self._fallback_cpu_embedding(texts)

    def _safe_encode(self, texts: List[str]) -> np.ndarray:
        """Safely encode texts with CUDA error handling."""
        try:
            # First try with the configured device
            return self.sentence_model.encode(
                texts,
                batch_size=len(texts),
                show_progress_bar=False,
                device=self.device
            )
        except RuntimeError as e:
            error_msg = str(e)
            # Check for CUDA errors
            if "CUDA" in error_msg or "device-side assert" in error_msg or "cuda" in error_msg.lower():
                print(f"❌ CUDA error detected in embedding generation: {e}")
                print("🔄 Clearing CUDA cache and switching to CPU...")

                # Clear CUDA cache
                self._clear_cuda_cache()

                # Mark CUDA as failed and switch to CPU permanently
                self._cuda_failed = True
                self.device = torch.device('cpu')

                # Try CPU fallback
                return self._fallback_cpu_embedding(texts)
            else:
                # Re-raise non-CUDA errors
                raise e
        except Exception as e:
            # Catch any other errors and try CPU fallback
            print(f"❌ Unexpected error in embedding generation: {e}")
            return self._fallback_cpu_embedding(texts)

    def _fallback_cpu_embedding(self, texts: List[str]) -> np.ndarray:
        """Fallback to CPU-only embedding generation with enhanced error handling."""
        try:
            print("🔄 Falling back to CPU for embedding generation...")

            # Ensure we're using CPU device
            cpu_device = torch.device('cpu')

            # Try encoding on CPU
            embeddings = self.sentence_model.encode(
                texts,
                batch_size=min(len(texts), 32),  # Smaller batch size for CPU
                show_progress_bar=False,
                device=cpu_device
            )
            print(f"✓ Successfully generated {len(texts)} embeddings on CPU")
            return embeddings

        except RuntimeError as e:
            # Handle any remaining CUDA errors
            if "cuda" in str(e).lower():
                print(f"❌ CUDA error persists even on CPU fallback: {e}")
                # Try one more time with explicit CPU device and smaller batches
                try:
                    embeddings = []
                    for text in texts:
                        emb = self.sentence_model.encode(
                            [text],
                            batch_size=1,
                            show_progress_bar=False,
                            device='cpu'
                        )
                        embeddings.append(emb[0])
                    print(f"✓ Generated {len(embeddings)} embeddings one-by-one on CPU")
                    return np.array(embeddings)
                except Exception as retry_error:
                    print(f"❌ Individual encoding also failed: {retry_error}")
            else:
                print(f"❌ CPU fallback failed with non-CUDA error: {e}")

        except Exception as e:
            print(f"❌ CPU fallback failed: {e}")

        # Last resort: return zero embeddings
        print("⚠️  Returning zero embeddings as last resort")
        embedding_dim = 384  # all-MiniLM-L6-v2 embedding dimension
        return np.zeros((len(texts), embedding_dim))
    
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
        """Split text into overlapping chunks (backward compatibility)."""
        return self.chunk_text_smart(text, chunk_tokens=int(chunk_size/1.3), overlap_tokens=int(overlap/1.3))

    def chunk_text_smart(self, text: str, chunk_tokens: int = 500, overlap_tokens: int = 50) -> List[str]:
        """
        Smart token-aware chunking inspired by kb/ingest.py.

        Args:
            text: Text to chunk
            chunk_tokens: Approximate tokens per chunk (default 500)
            overlap_tokens: Approximate token overlap (default 50)

        Returns:
            List of text chunks
        """
        if not text.strip():
            return []

        # Simple word-based approximation (1 word ≈ 1.3 tokens)
        words = text.split()
        chunk_words = int(chunk_tokens * 0.77)  # Approximate conversion
        overlap_words = int(overlap_tokens * 0.77)

        if len(words) <= chunk_words:
            return [text]

        chunks = []
        i = 0

        while i < len(words):
            chunk_end = min(i + chunk_words, len(words))
            chunk = " ".join(words[i:chunk_end])

            # Try to break at sentence boundaries for better chunks
            if chunk_end < len(words):
                # Look for sentence endings near the chunk boundary
                chunk_text = " ".join(words[i:chunk_end])
                last_period = chunk_text.rfind('.')
                last_exclamation = chunk_text.rfind('!')
                last_question = chunk_text.rfind('?')

                best_break = max(last_period, last_exclamation, last_question)

                # If we found a good sentence break in the last quarter of the chunk
                if best_break > len(chunk_text) * 0.75:
                    # Count words up to the sentence break
                    words_to_break = len(chunk_text[:best_break + 1].split())
                    chunk_end = i + words_to_break
                    chunk = " ".join(words[i:chunk_end])

            chunks.append(chunk.strip())

            if chunk_end >= len(words):
                break

            # Move forward with overlap
            i += max(1, chunk_words - overlap_words)

        return [chunk for chunk in chunks if chunk.strip()]