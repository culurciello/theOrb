from typing import Dict, Any, List, Optional, Callable
from .base_tool import BaseTool
import requests
import os
import time
import shutil
import uuid
from pathlib import Path
from urllib.parse import quote


class SearchDOAJTool(BaseTool):
    """Tool for searching DOAJ (Directory of Open Access Journals)."""

    BASE_URL = "https://doaj.org/api"
    API_VERSION = "v4"

    def __init__(self):
        self.temp_dir = "temp"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DOAJ-Search-Tool/1.0',
            'Accept': 'application/json'
        })

    def get_name(self) -> str:
        return "search_doaj"

    def get_description(self) -> str:
        return "Search the Directory of Open Access Journals (DOAJ) for open access articles and journals. Results are saved to a new collection. Auto-generates collection name if not provided. Use this when you need to find open access academic articles and journals."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for DOAJ (e.g., 'climate change', 'machine learning', 'cancer research')"
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional name for the collection. If not provided, auto-generates as 'doaj_search_XXX'"
                },
                "search_type": {
                    "type": "string",
                    "description": "Type of content to search: 'articles' or 'journals' (default: 'articles')",
                    "enum": ["articles", "journals"],
                    "default": "articles"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to retrieve (default: 10, max: 50)",
                    "default": 10
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
            search_type = kwargs.get("search_type", "articles")
            max_results = min(kwargs.get("max_results", 10), 50)

            if not query:
                return {"error": "Query parameter is required"}

            notify_progress("doaj_search", f"Starting DOAJ {search_type} search for: {query[:50]}...")

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
                collection_name = f"doaj_{search_type}_{query_short}_{timestamp}"

            notify_progress("doaj_search", "Preparing search environment...")

            # Clean up temp directory before starting
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

            # Create unique session directory
            session_id = str(int(time.time()))
            output_folder = os.path.join(self.temp_dir, f"doaj_{session_id}")
            Path(output_folder).mkdir(parents=True, exist_ok=True)

            # Search DOAJ
            notify_progress("doaj_search", f"Searching DOAJ database (max {max_results} results)...")

            # Calculate page size - DOAJ max is 100 per page
            page_size = min(max_results, 100)
            search_results = self._search_doaj(query, search_type, page_size)

            if not search_results or search_results.get('total', 0) == 0:
                notify_progress("doaj_search", "No results found for this query")
                return {
                    "success": True,
                    "message": "No results found for this query",
                    "results": [],
                    "output_folder": output_folder
                }

            results = search_results.get('results', [])[:max_results]
            total_found = search_results.get('total', 0)

            notify_progress("doaj_search", f"Found {total_found} total, processing {len(results)} results...")

            # Save results as text files
            saved_count = 0
            items = []

            for i, result in enumerate(results):
                bibjson = result.get('bibjson', {})
                title = bibjson.get('title', 'No title')[:60]

                notify_progress("doaj_search", f"Processing {search_type[:-1]} {i+1}/{len(results)}: {title}...")

                # Save result as text file
                text_file = self._save_result_as_text(result, i, search_type, output_folder)
                if text_file:
                    saved_count += 1

                # Format item data based on type
                if search_type == 'articles':
                    items.append({
                        "title": bibjson.get('title', ''),
                        "journal": bibjson.get('journal', {}).get('title', ''),
                        "year": bibjson.get('year', ''),
                        "doi": self._extract_doi(bibjson),
                        "abstract": bibjson.get('abstract', '')[:200] + "..." if len(bibjson.get('abstract', '')) > 200 else bibjson.get('abstract', ''),
                        "file": text_file
                    })
                else:  # journals
                    items.append({
                        "title": bibjson.get('title', ''),
                        "publisher": bibjson.get('publisher', {}).get('name', ''),
                        "issn": bibjson.get('pissn') or bibjson.get('eissn', ''),
                        "country": bibjson.get('publisher', {}).get('country', ''),
                        "file": text_file
                    })

                # Be respectful to servers
                time.sleep(0.3)

            # Save all files to a collection
            notify_progress("doaj_search", f"Creating collection '{collection_name}'...")
            collection_result = self._save_to_collection(output_folder, collection_name, user_id, notify_progress)

            if "error" in collection_result:
                notify_progress("doaj_search", f"Error: {collection_result['error']}")
                return {
                    "success": False,
                    "error": collection_result["error"],
                    "results_found": len(results),
                    "results_saved": saved_count
                }

            notify_progress("doaj_search", f"✓ Complete! Saved {saved_count} {search_type}. Collection created with {collection_result.get('files_processed')} documents indexed.")

            return {
                "success": True,
                "query": query,
                "search_type": search_type,
                "total_found": total_found,
                "total_results": len(results),
                "results_saved": saved_count,
                "collection_id": collection_result.get("collection_id"),
                "collection_name": collection_name,
                "files_indexed": collection_result.get("files_processed"),
                "total_chunks": collection_result.get("total_chunks"),
                "items": items,
                "message": f"Found {total_found} {search_type}, saved {saved_count} documents. Created collection '{collection_name}' with {collection_result.get('files_processed')} indexed documents."
            }

        except Exception as e:
            notify_progress("doaj_search", f"Error: {str(e)}")
            return {"error": f"DOAJ search failed: {str(e)}"}

    def _search_doaj(self, query: str, search_type: str, page_size: int = 10) -> Dict[str, Any]:
        """
        Search DOAJ API.

        Args:
            query: Search query string
            search_type: 'articles' or 'journals'
            page_size: Number of results per page (max 100)

        Returns:
            API response as dictionary
        """
        # Validate page size
        if page_size > 100:
            page_size = 100

        # Construct URL with query in the path
        url = f"{self.BASE_URL}/search/{search_type}/{quote(query)}"

        # Build request parameters
        params = {
            'page': 1,
            'pageSize': page_size
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during DOAJ API request: {e}")
            return {'error': str(e), 'results': [], 'total': 0}

    def _extract_doi(self, bibjson: Dict[str, Any]) -> str:
        """Extract DOI from bibjson."""
        identifiers = bibjson.get('identifier', [])
        for identifier in identifiers:
            if identifier.get('type') == 'doi':
                return identifier.get('id', '')
        return ''

    def _save_result_as_text(self, result: Dict[str, Any], index: int,
                            search_type: str, output_folder: str) -> str:
        """Save DOAJ search result as a formatted text file."""
        bibjson = result.get('bibjson', {})
        title = bibjson.get('title', 'Untitled')

        # Sanitize filename
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        filename = os.path.join(output_folder, f"DOAJ_{search_type[:-1]}_{index+1}_{safe_title}.txt")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"DOAJ - {search_type.upper()[:-1]}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"TITLE:\n{title}\n\n")

            if search_type == 'articles':
                # Article-specific fields
                authors = ', '.join([author.get('name', '') for author in bibjson.get('author', [])])
                if authors:
                    f.write(f"AUTHORS:\n{authors}\n\n")

                journal = bibjson.get('journal', {}).get('title', '')
                if journal:
                    f.write(f"JOURNAL: {journal}")
                    year = bibjson.get('year')
                    if year:
                        f.write(f" ({year})")
                    f.write("\n\n")

                doi = self._extract_doi(bibjson)
                if doi:
                    f.write(f"DOI: {doi}\n")
                    f.write(f"URL: https://doi.org/{doi}\n\n")

                # Subjects
                subjects = ', '.join([subj.get('term', '') for subj in bibjson.get('subject', [])])
                if subjects:
                    f.write(f"SUBJECTS:\n{subjects}\n\n")

                # Abstract
                abstract = bibjson.get('abstract', '')
                if abstract:
                    f.write("ABSTRACT:\n")
                    f.write("-" * 80 + "\n")
                    f.write(abstract)
                    f.write("\n" + "-" * 80 + "\n\n")

            else:  # journals
                # Journal-specific fields
                publisher = bibjson.get('publisher', {}).get('name', '')
                country = bibjson.get('publisher', {}).get('country', '')
                if publisher:
                    f.write(f"PUBLISHER: {publisher}")
                    if country:
                        f.write(f" ({country})")
                    f.write("\n\n")

                issn = bibjson.get('pissn', '')
                eissn = bibjson.get('eissn', '')
                if issn or eissn:
                    f.write("ISSN:\n")
                    if issn:
                        f.write(f"  Print: {issn}\n")
                    if eissn:
                        f.write(f"  Electronic: {eissn}\n")
                    f.write("\n")

                # Subjects
                subjects = ', '.join([subj.get('term', '') for subj in bibjson.get('subject', [])])
                if subjects:
                    f.write(f"SUBJECTS:\n{subjects}\n\n")

                # License
                licenses = ', '.join([lic.get('type', '') for lic in bibjson.get('license', [])])
                if licenses:
                    f.write(f"LICENSE: {licenses}\n\n")

                # APC info
                apc_info = bibjson.get('apc', {})
                has_apc = apc_info.get('has_apc', False)
                f.write(f"ARTICLE PROCESSING CHARGES: {'Yes' if has_apc else 'No'}\n\n")

            f.write("SOURCE: Directory of Open Access Journals (DOAJ)\n")
            f.write("https://doaj.org/\n")

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
                notify_progress("doaj_search", f"Found {len(all_files)} files to process")

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
                    notify_progress("doaj_search", "Creating collection in database...")

                # Create collection
                collection = Collection(
                    user_id=user_id,
                    name=collection_name,
                    description=f"DOAJ open access resources: {len(all_files)} documents",
                    source_type='doaj',
                    source_path=output_folder
                )
                db.session.add(collection)
                db.session.flush()

                # Initialize processors
                doc_processor = DocumentProcessor()
                vector_store = VectorStore()

                if notify_progress:
                    notify_progress("doaj_search", f"Processing and indexing {len(all_files)} documents...")

                # Process all files
                processed_docs = []
                all_chunks = []
                all_chunk_ids = []
                all_metadata = []

                for idx, file_path in enumerate(all_files):
                    try:
                        if notify_progress:
                            filename = os.path.basename(file_path)
                            notify_progress("doaj_search", f"Indexing document {idx+1}/{len(all_files)}: {filename[:40]}...")

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
                    notify_progress("doaj_search", f"Adding {len(all_chunks)} chunks to vector store...")

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
