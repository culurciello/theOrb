from typing import Dict, Any, List, Optional, Callable
from .base_tool import BaseTool
import os
import time
import shutil
import uuid
from pathlib import Path


class SearchLIITool(BaseTool):
    """Tool for searching Legal Information Institute (LII) using SerpAPI."""

    def __init__(self):
        self.temp_dir = "temp"

    def get_name(self) -> str:
        return "search_lii"

    def get_description(self) -> str:
        return "Search the Legal Information Institute (LII) at Cornell Law School for legal resources, statutes, regulations, and case law. Results are saved to a new collection. Auto-generates collection name if not provided. Use this when you need to find legal information and resources."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for LII (e.g., 'privacy law', 'first amendment', 'copyright')"
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional name for the collection. If not provided, auto-generates as 'lii_search_XXX'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to retrieve (default: 5, max: 20)",
                    "default": 5
                }
            },
            "required": ["query"]
        }

    def execute(self, progress_callback: Optional[Callable] = None, **kwargs) -> Dict[str, Any]:
        def notify_progress(status: str, message: str):
            """Helper to notify progress if callback is provided."""
            if progress_callback:
                progress_callback(status, message)

        try:
            query = kwargs.get("query")
            collection_name = kwargs.get("collection_name")
            max_results = min(kwargs.get("max_results", 5), 20)

            if not query:
                return {"error": "Query parameter is required"}

            notify_progress("lii_search", f"Starting LII search for: {query[:50]}...")

            # Get user_id from Flask session
            from flask_login import current_user

            if not current_user.is_authenticated:
                return {"error": "User not authenticated"}

            user_id = current_user.id

            # Auto-generate collection name if not provided
            if not collection_name:
                # Create a sanitized version of the query for the name
                query_short = query[:30].replace(' ', '_').replace('-', '_')
                # Remove special characters
                import re
                query_short = re.sub(r'[^a-zA-Z0-9_]', '', query_short)
                timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
                collection_name = f"lii_search_{query_short}_{timestamp}"

            notify_progress("lii_search", "Preparing search environment...")

            # Clean up temp directory before starting
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

            # Create unique session directory
            session_id = str(int(time.time()))
            output_folder = os.path.join(self.temp_dir, f"lii_{session_id}")
            Path(output_folder).mkdir(parents=True, exist_ok=True)

            # Search LII using SerpAPI
            notify_progress("lii_search", f"Searching LII database (max {max_results} results)...")
            results = self._search_lii_serpapi(query, max_results)

            if not results:
                notify_progress("lii_search", "No results found for this query")
                return {
                    "success": True,
                    "message": "No results found for this query",
                    "results": [],
                    "output_folder": output_folder
                }

            notify_progress("lii_search", f"Found {len(results)} results! Processing...")

            # Save results as text files
            saved_count = 0
            legal_resources = []

            for i, result in enumerate(results):
                title = result.get('title', 'No title')[:60]
                notify_progress("lii_search", f"Processing result {i+1}/{len(results)}: {title}...")

                # Save result as text file
                text_file = self._save_result_as_text(result, i, output_folder)
                if text_file:
                    saved_count += 1

                legal_resources.append({
                    "title": result.get('title', ''),
                    "url": result.get('url', ''),
                    "snippet": result.get('snippet', ''),
                    "file": text_file
                })

                # Be respectful to servers
                time.sleep(0.3)

            # Save all files to a collection
            notify_progress("lii_search", f"Creating collection '{collection_name}'...")
            collection_result = self._save_to_collection(output_folder, collection_name, user_id, notify_progress)

            if "error" in collection_result:
                notify_progress("lii_search", f"Error: {collection_result['error']}")
                return {
                    "success": False,
                    "error": collection_result["error"],
                    "results_found": len(results),
                    "results_saved": saved_count
                }

            notify_progress("lii_search", f"✓ Complete! Saved {saved_count} legal resources. Collection created with {collection_result.get('files_processed')} documents indexed.")

            return {
                "success": True,
                "query": query,
                "total_results": len(results),
                "results_saved": saved_count,
                "collection_id": collection_result.get("collection_id"),
                "collection_name": collection_name,
                "files_indexed": collection_result.get("files_processed"),
                "total_chunks": collection_result.get("total_chunks"),
                "resources": legal_resources,
                "message": f"Found {len(results)} legal resources, saved {saved_count} documents. Created collection '{collection_name}' with {collection_result.get('files_processed')} indexed documents."
            }

        except Exception as e:
            notify_progress("lii_search", f"Error: {str(e)}")
            return {"error": f"LII search failed: {str(e)}"}

    def _search_lii_serpapi(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search LII using SerpAPI for reliable results.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of dicts with keys: title, url, snippet
        """
        try:
            from serpapi import GoogleSearch
        except ImportError:
            print("❌ SerpAPI not installed. Run: pip install google-search-results")
            return []

        # Get API key from environment
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            print("❌ No API key provided. Set SERPAPI_KEY environment variable.")
            print("   Sign up at: https://serpapi.com")
            return []

        # Build search query
        search_query = f"site:law.cornell.edu {query}"

        params = {
            "q": search_query,
            "api_key": api_key,
            "num": num_results,
        }

        try:
            search = GoogleSearch(params)
            results_data = search.get_dict()

            results = []
            organic_results = results_data.get("organic_results", [])

            for item in organic_results[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })

            return results

        except Exception as e:
            print(f"❌ SerpAPI error: {e}")
            return []

    def _save_result_as_text(self, result: Dict[str, str], index: int, output_folder: str) -> str:
        """Save LII search result as a formatted text file."""
        title = result.get('title', 'Untitled')
        # Sanitize filename
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        filename = os.path.join(output_folder, f"LII_{index+1}_{safe_title}.txt")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("LEGAL INFORMATION INSTITUTE (LII) RESOURCE\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"TITLE:\n{result.get('title', 'No title')}\n\n")
            f.write(f"URL:\n{result.get('url', 'No URL')}\n\n")

            if result.get('snippet'):
                f.write("DESCRIPTION:\n")
                f.write("-" * 80 + "\n")
                f.write(result['snippet'])
                f.write("\n" + "-" * 80 + "\n\n")

            f.write("SOURCE: Cornell Law School - Legal Information Institute\n")
            f.write("https://www.law.cornell.edu/\n")

        return filename

    def _save_to_collection(self, output_folder: str, collection_name: str, user_id: int,
                            notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
        """Save downloaded files to a new collection."""
        try:
            # Get all files in output folder
            all_files = []
            for root, dirs, files in os.walk(output_folder):
                for file in files:
                    if file.lower().endswith('.txt'):
                        all_files.append(os.path.join(root, file))

            if not all_files:
                return {"error": "No files to save to collection"}

            if notify_progress:
                notify_progress("lii_search", f"Found {len(all_files)} files to process")

            # Import Flask dependencies (already in app context from tool execution)
            from models import Collection, Document, DocumentChunk
            from database import db
            from pipelines.document_processor import DocumentProcessor
            from vector_store import VectorStore

            # Already in Flask app context, use existing session
            try:
                # Check if collection already exists
                existing = Collection.query.filter_by(name=collection_name, user_id=user_id).first()
                if existing:
                    return {"error": f"Collection '{collection_name}' already exists"}

                if notify_progress:
                    notify_progress("lii_search", "Creating collection in database...")

                # Create collection
                collection = Collection(
                    user_id=user_id,
                    name=collection_name,
                    description=f"LII legal resources: {len(all_files)} documents",
                    source_type='lii',
                    source_path=output_folder
                )
                db.session.add(collection)
                db.session.flush()

                # Initialize processors
                doc_processor = DocumentProcessor()
                vector_store = VectorStore()

                if notify_progress:
                    notify_progress("lii_search", f"Processing and indexing {len(all_files)} documents...")

                # Process all files
                processed_docs = []
                all_chunks = []
                all_chunk_ids = []
                all_metadata = []

                for idx, file_path in enumerate(all_files):
                    try:
                        if notify_progress:
                            filename = os.path.basename(file_path)
                            notify_progress("lii_search", f"Indexing document {idx+1}/{len(all_files)}: {filename[:40]}...")

                        result = self._process_file(file_path, collection.id, doc_processor)
                        if result:
                            document, chunks, chunk_ids, metadata = result
                            processed_docs.append(document)
                            all_chunks.extend(chunks)
                            all_chunk_ids.extend(chunk_ids)
                            all_metadata.extend(metadata)
                    except Exception as e:
                        continue

                if not processed_docs:
                    db.session.rollback()
                    return {"error": "No files could be processed"}

                if notify_progress:
                    notify_progress("lii_search", f"Adding {len(all_chunks)} chunks to vector store...")

                # Add to vector store
                vector_store.add_document_chunks(
                    collection.name,
                    all_chunks,
                    all_chunk_ids,
                    all_metadata
                )

                # Commit all changes
                db.session.commit()

                # Clean up temp directory
                try:
                    shutil.rmtree(output_folder)
                except:
                    pass

                return {
                    "success": True,
                    "collection_id": collection.id,
                    "files_processed": len(processed_docs),
                    "total_chunks": len(all_chunks)
                }
            except Exception as db_error:
                db.session.rollback()
                raise db_error

        except Exception as e:
            return {"error": f"Failed to save to collection: {str(e)}"}

    def _process_file(self, file_path: str, collection_id: int, doc_processor) -> tuple:
        """Process a single file and create database records."""
        from models import Document, DocumentChunk
        from database import db

        filename = os.path.basename(file_path)

        # Process the file
        doc_data = doc_processor.process_file(file_path)
        if not doc_data:
            return None

        # Create permanent storage
        collection_upload_dir = os.path.join('uploads', f'collection_{collection_id}')
        os.makedirs(collection_upload_dir, exist_ok=True)
        stored_filename = f"{uuid.uuid4()}_{filename}"
        stored_file_path = os.path.join(collection_upload_dir, stored_filename)

        shutil.copy2(file_path, stored_file_path)

        # Generate access URL
        original_file_url = f"/api/files/collection_{collection_id}/{stored_filename}"

        # Calculate file size: use metadata if available, otherwise use content length
        metadata_file_size = doc_data['metadata'].get('file_size', 0) if doc_data.get('metadata') else 0
        content_length = len(doc_data['content']) if doc_data.get('content') else 0
        calculated_file_size = metadata_file_size if metadata_file_size > 0 else content_length

        # Create document record
        document = Document(
            filename=filename,
            file_path=filename,
            stored_file_path=stored_file_path,
            original_file_url=original_file_url,
            content=doc_data['content'],
            summary=doc_data.get('summary', ''),
            file_type=doc_data['file_type'],
            file_size=calculated_file_size,
            mime_type=doc_data.get('mime_type'),
            collection_id=collection_id
        )

        if doc_data.get('categories'):
            document.set_categories(doc_data['categories'])
        if doc_data.get('metadata'):
            document.set_metadata(doc_data['metadata'])

        db.session.add(document)
        db.session.flush()

        # Create chunks
        chunks = doc_data['chunks']
        chunk_records = []
        chunk_ids = []
        metadata = []

        for i, chunk_content in enumerate(chunks):
            chunk_id = f"doc_{document.id}_chunk_{i}"
            chunk = DocumentChunk(
                document_id=document.id,
                content=chunk_content,
                chunk_index=i,
                embedding_id=chunk_id
            )
            chunk_records.append(chunk)
            chunk_ids.append(chunk_id)
            metadata.append({
                'document_id': document.id,
                'filename': filename,
                'chunk_index': i,
                'file_type': doc_data['file_type'],
                'categories': ','.join(doc_data.get('categories', [])),
                'summary': doc_data.get('summary', ''),
                'original_file_url': original_file_url,
                'stored_file_path': stored_file_path,
                'file_path': filename
            })

        db.session.add_all(chunk_records)
        return document, chunks, chunk_ids, metadata
