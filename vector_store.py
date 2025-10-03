import sqlite3
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from typing import List, Dict, Any, Optional, Tuple
import os
import uuid
from datetime import datetime
import json
from tqdm import tqdm
import time

try:
    import faiss
    FAISS_AVAILABLE = True
    print(f"\033[92m✓ FAISS available for accelerated vector indexing\033[0m")
except ImportError:
    FAISS_AVAILABLE = False
    print(f"\033[93m⚠️  FAISS not available, using NumPy only\033[0m")

class VectorStore:
    """
    Optimized vector store combining FAISS for fast similarity search
    and SQLite for metadata storage with GPU acceleration.
    """

    def __init__(self, persist_directory: str = "./mydocs_db",
                 embedding_model: str = "mixedbread-ai/mxbai-embed-large-v1"):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self.vector_dim = 1024  # mxbai-embed-large output dimension

        # File paths
        os.makedirs(persist_directory, exist_ok=True)
        self.sqlite_path = os.path.join(persist_directory, "metadata.db")
        self.embeddings_path = os.path.join(persist_directory, "embeddings.npy")
        self.faiss_index_path = os.path.join(persist_directory, "index.faiss")

        # Initialize components
        self.sqlite_conn = None
        self.faiss_index = None
        self._model = None
        self._tokenizer = None

        # GPU optimization
        self.device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        print(f"\033[95m🔧 VectorStore using device: {self.device}\033[0m")

        # Initialize database
        self._init_sqlite()

        # Load existing data if available
        self._load_existing_data()

    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            print(f"\033[96mLoading embedding model: {self.embedding_model}...\033[0m")
            self._tokenizer = AutoTokenizer.from_pretrained(self.embedding_model)
            # Use float32 on CPU to avoid dtype issues, float16 on GPU for speed
            model_dtype = torch.float32 if self.device.type == "cpu" else torch.float16
            self._model = AutoModel.from_pretrained(
                self.embedding_model,
                torch_dtype=model_dtype
            )
            self._model = self._model.to(self.device)
            self._model.eval()
        return self._model

    @property
    def tokenizer(self):
        """Lazy load the tokenizer."""
        if self._tokenizer is None:
            # This will trigger model loading which also loads tokenizer
            _ = self.model
        return self._tokenizer

    def _init_sqlite(self):
        """Initialize SQLite database with optimized schema."""
        self.sqlite_conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        cur = self.sqlite_conn.cursor()

        # Documents table - simplified schema
        cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            collection_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            summary TEXT,
            category TEXT,
            subcategory TEXT,
            total_chunks INTEGER DEFAULT 0,
            embedding_model TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        """)

        # Chunks table - core content storage
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT,
            chunk_order INTEGER,
            chunk_text TEXT NOT NULL,
            token_count INTEGER,
            vector_id INTEGER,
            embedding_model TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
        )
        """)

        # Create indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_vector_id ON chunks(vector_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)")

        self.sqlite_conn.commit()

    def _load_existing_data(self):
        """Load existing FAISS index and embeddings if available."""
        if FAISS_AVAILABLE and os.path.exists(self.faiss_index_path):
            try:
                self.faiss_index = faiss.read_index(self.faiss_index_path)
                print(f"\033[92m✓ Loaded existing FAISS index with {self.faiss_index.ntotal} vectors\033[0m")
            except Exception as e:
                print(f"\033[93m⚠️  Failed to load FAISS index: {e}\033[0m")

    @torch.no_grad()
    def batch_embed(self, texts: List[str], batch_size: Optional[int] = None) -> List[np.ndarray]:
        """
        Optimized batch embedding with GPU acceleration.
        """
        if batch_size is None:
            # Dynamic batch size based on device
            if self.device.type == "cuda":
                batch_size = min(128, 64 * 2)  # GPU optimization
            elif self.device.type == "mps":
                batch_size = min(96, 64 + 32)  # Apple Silicon optimization
            else:
                batch_size = 32  # CPU conservative

        embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        if total_batches > 1:
            print(f"\033[94m  Processing {len(texts)} texts in {total_batches} batches...\033[0m")

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]

            # Tokenize and move to device
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Forward pass with mixed precision only on GPU
            if self.device.type == "cuda":
                with torch.amp.autocast('cuda'):
                    outputs = self.model(**inputs)
            else:
                # CPU/MPS: no autocast to avoid dtype issues
                outputs = self.model(**inputs)

            # Mean pooling
            last_hidden = outputs.last_hidden_state
            # Ensure attention_mask has same dtype as hidden states to avoid mixed dtype errors
            attention_mask = inputs["attention_mask"].unsqueeze(-1).to(last_hidden.dtype)
            masked_hidden = last_hidden * attention_mask
            summed = masked_hidden.sum(dim=1)
            counts = attention_mask.sum(dim=1).clamp(min=1e-9)  # Prevent division by zero
            mean_pooled = summed / counts

            # Normalize for cosine similarity
            norms = torch.norm(mean_pooled, dim=1, keepdim=True).clamp(min=1e-9)
            mean_pooled = mean_pooled / norms

            # Convert to numpy - ensure float32 dtype
            embeddings.extend(mean_pooled.cpu().to(torch.float32).numpy())

            # Clear GPU cache periodically
            if self.device.type in ["cuda", "mps"] and i % (batch_size * 4) == 0:
                if self.device.type == "cuda":
                    torch.cuda.empty_cache()

        return embeddings

    def add_document(self, collection_name: str, file_path: str, content: str,
                    summary: str = "", categories: List[str] = None,
                    metadata: Dict[str, Any] = None, file_type: str = "text") -> str:
        """Add a document with automatic chunking and embedding."""
        doc_id = str(uuid.uuid4())

        # Smart chunking (token-based like kb/ examples)
        chunks = self._smart_chunk_text(content, chunk_tokens=500, overlap_tokens=50)

        # Generate embeddings for all chunks
        embeddings = self.batch_embed(chunks)

        # Get next vector IDs
        next_vector_id = self._get_next_vector_id()

        # Store document metadata
        category = categories[0] if categories else "general"
        subcategory = categories[1] if len(categories) > 1 else None

        cur = self.sqlite_conn.cursor()
        cur.execute("""
            INSERT INTO documents
            (doc_id, collection_name, file_path, file_type, summary, category, subcategory,
             total_chunks, embedding_model, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, collection_name, file_path, file_type, summary, category, subcategory,
              len(chunks), self.embedding_model, json.dumps(metadata or {})))

        # Store chunks and embeddings
        chunk_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            vector_id = next_vector_id + i

            cur.execute("""
                INSERT INTO chunks
                (chunk_id, doc_id, chunk_order, chunk_text, token_count, vector_id, embedding_model)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (chunk_id, doc_id, i, chunk, len(chunk.split()), vector_id, self.embedding_model))

            chunk_data.append((vector_id, embedding))

        self.sqlite_conn.commit()

        # Update vector index
        self._add_to_vector_index([emb for _, emb in chunk_data])

        print(f"\033[92m✓ Added document {file_path} with {len(chunks)} chunks\033[0m")
        return doc_id

    def _smart_chunk_text(self, text: str, chunk_tokens: int = 500, overlap_tokens: int = 50) -> List[str]:
        """Smart chunking based on tokens like kb/ examples."""
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
            chunks.append(chunk)

            if chunk_end >= len(words):
                break

            i += (chunk_words - overlap_words)

        return [chunk for chunk in chunks if chunk.strip()]

    def _get_next_vector_id(self) -> int:
        """Get the next available vector ID."""
        cur = self.sqlite_conn.cursor()
        cur.execute("SELECT MAX(vector_id) FROM chunks")
        result = cur.fetchone()
        return (result[0] or -1) + 1

    def _add_to_vector_index(self, embeddings: List[np.ndarray]):
        """Add embeddings to FAISS index."""
        if not embeddings:
            return

        embeddings_array = np.array(embeddings).astype('float32')

        if self.faiss_index is None and FAISS_AVAILABLE:
            # Create new FAISS index
            self.faiss_index = faiss.IndexFlatIP(self.vector_dim)  # Inner product for normalized vectors

        if self.faiss_index is not None:
            self.faiss_index.add(embeddings_array)
            # Save updated index
            faiss.write_index(self.faiss_index, self.faiss_index_path)

        # Also save to numpy file for fallback
        self._save_embeddings_numpy(embeddings_array)

    def _save_embeddings_numpy(self, new_embeddings: np.ndarray):
        """Save embeddings to numpy file for fallback."""
        if os.path.exists(self.embeddings_path):
            existing_embeddings = np.load(self.embeddings_path)
            all_embeddings = np.vstack([existing_embeddings, new_embeddings])
        else:
            all_embeddings = new_embeddings

        np.save(self.embeddings_path, all_embeddings)

    def retrieve_with_context(self, collection_name: str, query: str, top_k: int = 6,
                            context_window: int = 2, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Smart retrieval pipeline with context-aware search inspired by kb/query.py.

        Steps:
        1. Get main matches using similarity search
        2. Add neighboring chunks for context
        3. Filter by relevance and category
        4. Build enriched context
        """
        # Generate query embedding
        query_embeddings = self.batch_embed([query])
        query_embedding = query_embeddings[0]

        # 1. Get main similarity matches
        if self.faiss_index is not None:
            # Use FAISS for fast search
            scores, indices = self.faiss_index.search(
                query_embedding.reshape(1, -1).astype('float32'),
                top_k * 3  # Get more candidates for filtering
            )
            top_indices = indices[0]
            top_scores = scores[0]
        else:
            # Fallback to numpy similarity search
            if os.path.exists(self.embeddings_path):
                all_embeddings = np.load(self.embeddings_path)
                similarities = np.dot(all_embeddings, query_embedding)
                top_indices = np.argsort(similarities)[::-1][:top_k * 3]
                top_scores = similarities[top_indices]
            else:
                return []

        # 2. Build results with context
        results = []
        seen_chunks = set()
        cur = self.sqlite_conn.cursor()

        for vector_id, score in zip(top_indices, top_scores):
            # Apply category filter if specified
            if category_filter:
                cur.execute("""
                    SELECT c.chunk_id, c.doc_id, c.chunk_text, c.chunk_order,
                           d.category, d.subcategory, d.file_path
                    FROM chunks c
                    JOIN documents d ON c.doc_id = d.doc_id
                    WHERE c.vector_id = ? AND d.collection_name = ? AND d.category = ?
                """, (int(vector_id), collection_name, category_filter))
            else:
                cur.execute("""
                    SELECT c.chunk_id, c.doc_id, c.chunk_text, c.chunk_order,
                           d.category, d.subcategory, d.file_path
                    FROM chunks c
                    JOIN documents d ON c.doc_id = d.doc_id
                    WHERE c.vector_id = ? AND d.collection_name = ?
                """, (int(vector_id), collection_name))

            row = cur.fetchone()
            if not row:
                continue

            chunk_id, doc_id, chunk_text, chunk_order, category, subcategory, file_path = row

            # Add main matching chunk
            if chunk_id not in seen_chunks:
                results.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "chunk_text": chunk_text,
                    "category": category,
                    "subcategory": subcategory,
                    "file_path": file_path,
                    "score": float(score),
                    "is_main_match": True,
                    "chunk_order": chunk_order
                })
                seen_chunks.add(chunk_id)

            # 3. Add context chunks (neighboring chunks)
            for offset in range(-context_window, context_window + 1):
                if offset == 0:  # Skip main chunk
                    continue

                target_order = chunk_order + offset

                # Get neighboring chunk
                if category_filter:
                    cur.execute("""
                        SELECT c.chunk_id, c.doc_id, c.chunk_text, c.chunk_order,
                               d.category, d.subcategory, d.file_path
                        FROM chunks c
                        JOIN documents d ON c.doc_id = d.doc_id
                        WHERE c.chunk_order = ? AND c.doc_id = ? AND d.category = ?
                    """, (target_order, doc_id, category_filter))
                else:
                    cur.execute("""
                        SELECT c.chunk_id, c.doc_id, c.chunk_text, c.chunk_order,
                               d.category, d.subcategory, d.file_path
                        FROM chunks c
                        JOIN documents d ON c.doc_id = d.doc_id
                        WHERE c.chunk_order = ? AND c.doc_id = ?
                    """, (target_order, doc_id))

                context_row = cur.fetchone()
                if context_row:
                    ctx_chunk_id, ctx_doc_id, ctx_chunk_text, ctx_chunk_order, ctx_category, ctx_subcategory, ctx_file_path = context_row

                    if ctx_chunk_id not in seen_chunks:
                        results.append({
                            "chunk_id": ctx_chunk_id,
                            "doc_id": ctx_doc_id,
                            "chunk_text": ctx_chunk_text,
                            "category": ctx_category,
                            "subcategory": ctx_subcategory,
                            "file_path": ctx_file_path,
                            "score": float(score) * 0.8,  # Lower score for context
                            "is_main_match": False,
                            "context_offset": offset,
                            "chunk_order": ctx_chunk_order
                        })
                        seen_chunks.add(ctx_chunk_id)

            # Stop when we have enough main matches
            main_matches = len([r for r in results if r.get("is_main_match", False)])
            if main_matches >= top_k:
                break

        # 4. Sort results: main matches first, then by score
        results.sort(key=lambda x: (not x.get("is_main_match", False), -x["score"]))

        return results

    def search_similar_chunks(self, collection_name: str, query: str,
                            n_results: int = 5, filters: Optional[Dict[str, Any]] = None,
                            category_filter: str = None) -> List[Dict[str, Any]]:
        """Simple similarity search without context (backward compatibility)."""
        # Handle filters parameter for backward compatibility
        if filters and not category_filter:
            if 'categories' in filters:
                category_filter = filters['categories']
            elif 'category' in filters:
                category_filter = filters['category']
            elif 'file_type' in filters:
                # If filtering by file_type, use file type search
                return self.search_by_file_type(collection_name, filters['file_type'], n_results)
        results = self.retrieve_with_context(
            collection_name=collection_name,
            query=query,
            top_k=n_results,
            context_window=0,  # No context
            category_filter=category_filter
        )

        # Format for backward compatibility
        formatted_results = []
        for result in results[:n_results]:
            formatted_results.append({
                'content': result['chunk_text'],
                'metadata': {
                    'file_path': result['file_path'],
                    'category': result['category'],
                    'subcategory': result['subcategory'],
                    'chunk_order': result['chunk_order']
                },
                'distance': 1.0 - result['score'],  # Convert similarity to distance
                'chunk_id': result['chunk_id']
            })

        return formatted_results

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection."""
        cur = self.sqlite_conn.cursor()

        # Document count
        cur.execute("SELECT COUNT(*) FROM documents WHERE collection_name = ?", (collection_name,))
        doc_count = cur.fetchone()[0]

        # Chunk count
        cur.execute("""
            SELECT COUNT(*) FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.collection_name = ?
        """, (collection_name,))
        chunk_count = cur.fetchone()[0]

        # File types
        cur.execute("""
            SELECT file_type, COUNT(*) FROM documents
            WHERE collection_name = ?
            GROUP BY file_type
        """, (collection_name,))
        file_types = dict(cur.fetchall())

        # Categories
        cur.execute("""
            SELECT category, COUNT(*) FROM documents
            WHERE collection_name = ?
            GROUP BY category
        """, (collection_name,))
        categories = dict(cur.fetchall())

        return {
            "collection_name": collection_name,
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "file_types": file_types,
            "categories": categories,
            "has_faiss_index": self.faiss_index is not None,
            "embedding_model": self.embedding_model
        }

    def delete_collection(self, collection_name: str):
        """Delete all documents in a collection."""
        cur = self.sqlite_conn.cursor()

        # Get all doc_ids for the collection
        cur.execute("SELECT doc_id FROM documents WHERE collection_name = ?", (collection_name,))
        doc_ids = [row[0] for row in cur.fetchall()]

        if doc_ids:
            # Delete chunks
            placeholders = ','.join(['?'] * len(doc_ids))
            cur.execute(f"DELETE FROM chunks WHERE doc_id IN ({placeholders})", doc_ids)

            # Delete documents
            cur.execute("DELETE FROM documents WHERE collection_name = ?", (collection_name,))

            self.sqlite_conn.commit()
            print(f"\033[92m✓ Deleted collection {collection_name} with {len(doc_ids)} documents\033[0m")

    def add_document_chunks(self, collection_name: str, chunks: List[str],
                           chunk_ids: List[str], metadata: List[Dict[str, Any]]):
        """Add document chunks directly (backward compatibility with old API)."""
        if not chunks or not chunk_ids or not metadata:
            return

        # Generate embeddings for chunks
        embeddings = self.batch_embed(chunks)

        # Get next vector IDs
        next_vector_id = self._get_next_vector_id()

        # Create a synthetic document for these chunks
        doc_id = str(uuid.uuid4())

        # Extract info from first chunk's metadata
        first_meta = metadata[0] if metadata else {}
        file_path = first_meta.get('file_path', f'/synthetic/{collection_name}/{doc_id}')
        file_type = first_meta.get('file_type', 'text')
        categories = first_meta.get('categories', 'general').split(',') if first_meta.get('categories') else ['general']

        # Store document metadata
        cur = self.sqlite_conn.cursor()
        cur.execute("""
            INSERT INTO documents
            (doc_id, collection_name, file_path, file_type, summary, category, subcategory,
             total_chunks, embedding_model, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, collection_name, file_path, file_type,
              f"Document with {len(chunks)} chunks", categories[0],
              categories[1] if len(categories) > 1 else None,
              len(chunks), self.embedding_model, json.dumps(first_meta)))

        # Store chunks
        for i, (chunk, chunk_id, chunk_meta, embedding) in enumerate(zip(chunks, chunk_ids, metadata, embeddings)):
            vector_id = next_vector_id + i

            cur.execute("""
                INSERT INTO chunks
                (chunk_id, doc_id, chunk_order, chunk_text, token_count, vector_id, embedding_model)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (chunk_id, doc_id, i, chunk, len(chunk.split()), vector_id, self.embedding_model))

        self.sqlite_conn.commit()

        # Update vector index
        self._add_to_vector_index(embeddings)

        print(f"\033[92m✓ Added {len(chunks)} chunks to collection {collection_name}\033[0m")

    def search_by_category(self, collection_name: str, category: str,
                          n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for documents by category (backward compatibility)."""
        return self.search_similar_chunks(
            collection_name=collection_name,
            query=f"category:{category}",  # Use category as query
            n_results=n_results,
            category_filter=category
        )

    def search_by_file_type(self, collection_name: str, file_type: str,
                           n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for documents by file type (backward compatibility)."""
        cur = self.sqlite_conn.cursor()

        # Get chunks from documents of specified file type
        cur.execute("""
            SELECT c.chunk_id, c.chunk_text, c.chunk_order,
                   d.file_path, d.category, d.subcategory
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.collection_name = ? AND d.file_type = ?
            ORDER BY c.chunk_order
            LIMIT ?
        """, (collection_name, file_type, n_results))

        results = []
        for row in cur.fetchall():
            chunk_id, chunk_text, chunk_order, file_path, category, subcategory = row
            results.append({
                'content': chunk_text,
                'metadata': {
                    'file_path': file_path,
                    'file_type': file_type,
                    'category': category,
                    'subcategory': subcategory,
                    'chunk_order': chunk_order
                },
                'distance': 0.0,  # No distance for direct type match
                'chunk_id': chunk_id
            })

        return results

    def delete_document_chunks(self, collection_name: str, chunk_ids: List[str]):
        """Delete specific document chunks (backward compatibility)."""
        if not chunk_ids:
            return

        cur = self.sqlite_conn.cursor()

        # Delete chunks
        placeholders = ','.join(['?'] * len(chunk_ids))
        cur.execute(f"""
            DELETE FROM chunks
            WHERE chunk_id IN ({placeholders})
            AND doc_id IN (
                SELECT doc_id FROM documents WHERE collection_name = ?
            )
        """, chunk_ids + [collection_name])

        deleted_count = cur.rowcount
        self.sqlite_conn.commit()

        print(f"\033[92m✓ Deleted {deleted_count} chunks from collection {collection_name}\033[0m")

    def get_collection_summary(self, collection_name: str) -> Dict[str, Any]:
        """Get collection summary (backward compatibility)."""
        cur = self.sqlite_conn.cursor()

        # Get unique documents with summaries
        cur.execute("""
            SELECT file_path, file_type, category, subcategory, summary, created_at
            FROM documents
            WHERE collection_name = ?
            ORDER BY created_at DESC
        """, (collection_name,))

        summaries = []
        for row in cur.fetchall():
            file_path, file_type, category, subcategory, summary, created_at = row
            categories = [category]
            if subcategory:
                categories.append(subcategory)

            summaries.append({
                'file_path': file_path,
                'file_type': file_type,
                'categories': categories,
                'summary': summary or f"Document of type {file_type}",
                'created_at': created_at
            })

        return {
            'collection_name': collection_name,
            'total_files': len(summaries),
            'summaries': summaries
        }

    def get_collection_images(self, collection_name: str) -> List[Dict[str, Any]]:
        """Get all images in collection (backward compatibility)."""
        return self.search_by_file_type(collection_name, "image", n_results=1000)

    def search_with_context(self, collection_name: str, query: str,
                          n_results: int = 6, context_window: int = 2,
                          category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Smart context-aware search (alias for retrieve_with_context)."""
        return self.retrieve_with_context(
            collection_name=collection_name,
            query=query,
            top_k=n_results,
            context_window=context_window,
            category_filter=category_filter
        )

    def search_with_category_detection(self, collection_name: str, query: str,
                                     n_results: int = 6, context_window: int = 2) -> List[Dict[str, Any]]:
        """Search with automatic category detection."""
        # Use built-in category detection
        available_categories = self._get_collection_categories(collection_name)
        detected_category = self._detect_query_category(query, available_categories)

        results = self.search_with_context(
            collection_name=collection_name,
            query=query,
            n_results=n_results,
            context_window=context_window,
            category_filter=detected_category
        )

        # Add detection info
        for result in results:
            result['detected_category'] = detected_category

        return results

    def add_directory_documents(self, collection_name: str, processed_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add processed documents from directory ingestion (convenience method)."""
        stats = {
            'total_documents': 0,
            'total_chunks': 0,
            'file_types': {},
            'categories': {},
            'processed_files': []
        }

        for doc in processed_docs:
            if not doc or 'error' in doc:
                continue

            try:
                # Extract document info
                file_path = doc['file_path']
                file_type = doc.get('file_type', 'text')
                content = doc.get('content', '')
                summary = doc.get('summary', '')
                categories = doc.get('categories', ['general'])
                metadata = doc.get('metadata', {})

                # Add document to store
                doc_id = self.add_document(
                    collection_name=collection_name,
                    file_path=file_path,
                    content=content,
                    summary=summary,
                    categories=categories,
                    metadata=metadata,
                    file_type=file_type
                )

                # Update stats
                stats['total_documents'] += 1
                stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
                for category in categories:
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1

                # Get chunk count from store
                collection_stats = self.get_collection_stats(collection_name)
                stats['total_chunks'] = collection_stats.get('chunk_count', 0)

                stats['processed_files'].append({
                    'path': file_path,
                    'type': file_type,
                    'categories': categories,
                    'doc_id': doc_id
                })

            except Exception as e:
                print(f"\033[91m❌ Error adding document {doc.get('file_path', 'unknown')}: {e}\033[0m")
                continue

        return stats

    def search_images_by_keywords(self, collection_name: str, keywords: str,
                                n_results: int = 10) -> List[Dict[str, Any]]:
        """Search images by keywords."""
        # Use file type search for images
        return self.search_by_file_type(collection_name, "image", n_results)

    def get_performance_info(self) -> Dict[str, Any]:
        """Get performance and capability information."""
        info = {
            'backend': 'optimized',
            'features': {
                'faiss_acceleration': FAISS_AVAILABLE,
                'context_aware_search': True,
                'smart_chunking': True,
                'category_detection': True,
                'gpu_optimization': True,
                'batch_processing': True,
                'image_search': True
            },
            'performance': {
                'search_speed': 'Very Fast (FAISS)' if FAISS_AVAILABLE else 'Fast (NumPy)',
                'embedding_speed': 'Fast (GPU optimized)',
                'storage_efficiency': 'High (SQLite + NumPy)',
                'memory_usage': 'Optimized'
            }
        }

        # Get device info
        info['device'] = str(self.device)
        return info

    def close(self):
        """Close database connections."""
        if self.sqlite_conn:
            self.sqlite_conn.close()


def create_vector_store(**kwargs) -> VectorStore:
    """
    Factory function to create a vector store.

    Args:
        **kwargs: Additional arguments for the vector store

    Returns:
        VectorStore instance
    """
    return VectorStore(**kwargs)