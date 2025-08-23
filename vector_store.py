import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import os
import uuid
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class VectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB vector store with sentence transformers."""
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Store CLIP embeddings separately for image similarity search
        self.image_embeddings = {}  # {collection_name: {file_path: embedding}}
        
    def get_or_create_collection(self, collection_name: str):
        """Get or create a ChromaDB collection for a document collection."""
        return self.client.get_or_create_collection(
            name=f"orb_{collection_name}",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_document_chunks(self, collection_name: str, chunks: List[str], 
                           chunk_ids: List[str], metadata: List[Dict[str, Any]]):
        """Add document chunks to the vector store."""
        collection = self.get_or_create_collection(collection_name)
        
        # Generate embeddings
        embeddings = self.model.encode(chunks).tolist()
        
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadata,
            ids=chunk_ids
        )
    
    def add_directory_documents(self, collection_name: str, processed_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add processed documents from directory ingestion to the vector store."""
        collection = self.get_or_create_collection(collection_name)
        
        all_chunks = []
        all_chunk_ids = []
        all_metadata = []
        
        stats = {
            'total_documents': len(processed_docs),
            'total_chunks': 0,
            'file_types': {},
            'categories': {},
            'processed_files': []
        }
        
        for doc in processed_docs:
            if not doc:  # Skip None documents
                continue
                
            file_path = doc['file_path']
            file_type = doc['file_type']
            chunks = doc['chunks']
            categories = doc['categories']
            doc_metadata = doc['metadata']
            summary = doc.get('summary', '')
            
            # Update statistics
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
            for category in categories:
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
            stats['processed_files'].append({
                'path': file_path,
                'type': file_type,
                'chunks': len(chunks),
                'categories': categories
            })
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                chunk_id = f"{uuid.uuid4()}_{i}"
                
                # Create comprehensive metadata
                # Convert lists and complex objects to strings for ChromaDB compatibility
                safe_metadata = {}
                for key, value in doc_metadata.items():
                    if isinstance(value, (list, dict)):
                        safe_metadata[key] = str(value)
                    elif isinstance(value, (str, int, float, bool)) or value is None:
                        safe_metadata[key] = value
                    else:
                        safe_metadata[key] = str(value)
                
                chunk_metadata = {
                    'file_path': file_path,
                    'file_type': file_type,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'categories': ','.join(categories) if categories else '',  # Convert to comma-separated string
                    'summary': summary,
                    'created_at': datetime.utcnow().isoformat(),
                    **safe_metadata  # Include file-specific metadata
                }
                
                # Add file access URLs if available
                if 'original_file_url' in doc:
                    chunk_metadata['original_file_url'] = doc['original_file_url']
                if 'stored_file_path' in doc:
                    chunk_metadata['stored_file_path'] = doc['stored_file_path']
                
                # Store CLIP embeddings for images
                if file_type == 'image' and 'clip_embedding' in doc:
                    if collection_name not in self.image_embeddings:
                        self.image_embeddings[collection_name] = {}
                    self.image_embeddings[collection_name][file_path] = np.array(doc['clip_embedding'])
                
                all_chunks.append(chunk)
                all_chunk_ids.append(chunk_id)
                all_metadata.append(chunk_metadata)
        
        stats['total_chunks'] = len(all_chunks)
        
        if all_chunks:
            # Generate embeddings
            embeddings = self.model.encode(all_chunks).tolist()
            
            # Add to ChromaDB
            collection.add(
                embeddings=embeddings,
                documents=all_chunks,
                metadatas=all_metadata,
                ids=all_chunk_ids
            )
        
        return stats
    
    def search_similar_chunks(self, collection_name: str, query: str, 
                            n_results: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar chunks in a collection with optional filtering."""
        collection = self.get_or_create_collection(collection_name)
        
        # Generate query embedding
        query_embedding = self.model.encode([query]).tolist()
        
        # Prepare query parameters
        query_params = {
            'query_embeddings': query_embedding,
            'n_results': n_results
        }
        
        # Add filters if provided
        if filters:
            query_params['where'] = filters
        
        results = collection.query(**query_params)
        
        # Format results
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if results['distances'] else None,
                'chunk_id': results['ids'][0][i] if results['ids'] else None
            })
        
        return formatted_results
    
    def search_similar_images_by_embedding(self, collection_name: str, query_embedding: np.ndarray, 
                                         n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for similar images using CLIP embeddings."""
        if collection_name not in self.image_embeddings:
            return []
        
        image_embeds = self.image_embeddings[collection_name]
        if not image_embeds:
            return []
        
        # Calculate similarities
        similarities = []
        for file_path, embedding in image_embeds.items():
            similarity = cosine_similarity([query_embedding], [embedding])[0][0]
            similarities.append((file_path, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top results and fetch metadata
        results = []
        collection = self.get_or_create_collection(collection_name)
        
        for file_path, similarity in similarities[:n_results]:
            # Find chunks from this image file
            chunks = collection.get(where={"file_path": file_path})
            if chunks['documents']:
                results.append({
                    'content': chunks['documents'][0],
                    'metadata': chunks['metadatas'][0],
                    'similarity': float(similarity),
                    'chunk_id': chunks['ids'][0]
                })
        
        return results
    
    def search_images_by_keywords(self, collection_name: str, keywords: str, 
                                n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for images based on text keywords using regular text search."""
        # Use regular text search but filter for images
        return self.search_similar_chunks(
            collection_name, 
            keywords,
            n_results, 
            filters={"file_type": "image"}
        )
    
    def search_by_category(self, collection_name: str, category: str, 
                          n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for documents by category."""
        collection = self.get_or_create_collection(collection_name)
        
        # Since categories are now comma-separated strings, we need to search differently
        all_data = collection.get()
        
        # Filter by category manually
        filtered_docs = []
        filtered_metadata = []
        filtered_ids = []
        
        for i, metadata in enumerate(all_data['metadatas']):
            categories_str = metadata.get('categories', '')
            if category.lower() in categories_str.lower():
                filtered_docs.append(all_data['documents'][i])
                filtered_metadata.append(metadata)
                filtered_ids.append(all_data['ids'][i])
                
                if len(filtered_docs) >= n_results:
                    break
        
        results = {
            'documents': filtered_docs,
            'metadatas': filtered_metadata,
            'ids': filtered_ids
        }
        
        formatted_results = []
        for i in range(len(results['documents'])):
            formatted_results.append({
                'content': results['documents'][i],
                'metadata': results['metadatas'][i],
                'chunk_id': results['ids'][i]
            })
        
        return formatted_results
    
    def search_by_file_type(self, collection_name: str, file_type: str, 
                           n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for documents by file type."""
        collection = self.get_or_create_collection(collection_name)
        
        results = collection.get(
            where={"file_type": file_type},
            limit=n_results
        )
        
        formatted_results = []
        for i in range(len(results['documents'])):
            formatted_results.append({
                'content': results['documents'][i],
                'metadata': results['metadatas'][i],
                'chunk_id': results['ids'][i]
            })
        
        return formatted_results
    
    def delete_collection(self, collection_name: str):
        """Delete a collection from the vector store."""
        try:
            self.client.delete_collection(name=f"orb_{collection_name}")
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")
    
    def delete_document_chunks(self, collection_name: str, chunk_ids: List[str]):
        """Delete specific document chunks from the vector store."""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=chunk_ids)
        except Exception as e:
            print(f"Error deleting chunks {chunk_ids} from collection {collection_name}: {e}")
    
    def delete_documents_by_file_path(self, collection_name: str, file_path: str):
        """Delete all chunks from a specific file."""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(where={"file_path": file_path})
        except Exception as e:
            print(f"Error deleting documents from {file_path} in collection {collection_name}: {e}")
    
    def get_collection_summary(self, collection_name: str) -> Dict[str, Any]:
        """Get a summary of all documents in a collection."""
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # Get documents with summaries
            all_data = collection.get()
            
            summaries = []
            seen_files = set()
            
            for i, metadata in enumerate(all_data['metadatas']):
                file_path = metadata.get('file_path')
                if file_path and file_path not in seen_files:
                    seen_files.add(file_path)
                    summaries.append({
                        'file_path': file_path,
                        'file_type': metadata.get('file_type'),
                        'categories': metadata.get('categories', []),
                        'summary': metadata.get('summary', ''),
                        'created_at': metadata.get('created_at')
                    })
            
            return {
                'collection_name': collection_name,
                'total_files': len(summaries),
                'summaries': summaries
            }
        except Exception as e:
            return {"error": str(e), "summaries": []}
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics about a collection."""
        try:
            collection = self.get_or_create_collection(collection_name)
            count = collection.count()
            
            # Get all metadata to analyze
            all_data = collection.get()
            
            stats = {
                "document_count": count,
                "file_types": {},
                "categories": {},
                "total_files": set()
            }
            
            for metadata in all_data['metadatas']:
                # Count file types
                file_type = metadata.get('file_type', 'unknown')
                stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
                
                # Count categories
                categories_str = metadata.get('categories', '')
                categories = [cat.strip() for cat in categories_str.split(',') if cat.strip()]
                for category in categories:
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1
                
                # Track unique files
                file_path = metadata.get('file_path')
                if file_path:
                    stats['total_files'].add(file_path)
            
            stats['unique_files'] = len(stats['total_files'])
            del stats['total_files']  # Remove set for JSON serialization
            
            return stats
        except Exception as e:
            return {"error": str(e), "document_count": 0}
    
    def get_collection_images(self, collection_name: str) -> List[Dict[str, Any]]:
        """Get all images in a collection."""
        return self.search_by_file_type(collection_name, "image", n_results=1000)