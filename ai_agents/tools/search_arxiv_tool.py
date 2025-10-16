from typing import Dict, Any, List, Optional, Callable
from .base_tool import BaseTool
import arxiv
import requests
import os
import time
import shutil
import uuid
from pathlib import Path


class SearchArxivTool(BaseTool):
    """Tool for searching arXiv and downloading research papers."""

    def __init__(self):
        # Initialize arXiv client
        self.client = arxiv.Client()
        self.temp_dir = "temp"

    def get_name(self) -> str:
        return "search_arxiv"

    def get_description(self) -> str:
        return "Search arXiv for research papers, download PDFs, and automatically save them to a new collection. Auto-generates collection name if not provided. Use this when you need to find and organize arXiv preprints and papers."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for arXiv (e.g., 'quantum computing', 'machine learning', 'ti:transformers AND cat:cs.AI')"
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional name for the collection. If not provided, auto-generates as 'arxiv_search_XXX'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of papers to retrieve (default: 10, max: 50)",
                    "default": 10
                },
                "sort_by": {
                    "type": "string",
                    "description": "Sort criterion: 'relevance', 'lastUpdatedDate', or 'submittedDate' (default: 'relevance')",
                    "default": "relevance",
                    "enum": ["relevance", "lastUpdatedDate", "submittedDate"]
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
            max_results = min(kwargs.get("max_results", 10), 50)
            sort_by = kwargs.get("sort_by", "relevance")

            if not query:
                return {"error": "Query parameter is required"}

            notify_progress("arxiv_search", f"Starting arXiv search for: {query[:50]}...")

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
                collection_name = f"arxiv_search_{query_short}_{timestamp}"

            notify_progress("arxiv_search", "Preparing search environment...")

            # Clean up temp directory before starting
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

            # Create unique session directory
            session_id = str(int(time.time()))
            output_folder = os.path.join(self.temp_dir, f"arxiv_{session_id}")
            Path(output_folder).mkdir(parents=True, exist_ok=True)

            # Map sort_by parameter to arXiv SortCriterion
            sort_criterion = arxiv.SortCriterion.Relevance
            if sort_by == "lastUpdatedDate":
                sort_criterion = arxiv.SortCriterion.LastUpdatedDate
            elif sort_by == "submittedDate":
                sort_criterion = arxiv.SortCriterion.SubmittedDate

            # Search arXiv
            notify_progress("arxiv_search", f"Searching arXiv database (max {max_results} results)...")
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_criterion
            )

            try:
                results = list(self.client.results(search))
            except Exception as e:
                notify_progress("arxiv_search", f"Search failed: {str(e)}")
                return {"error": f"arXiv search failed: {str(e)}"}

            if not results:
                notify_progress("arxiv_search", "No papers found for this query")
                return {
                    "success": True,
                    "message": "No papers found for this query",
                    "papers": [],
                    "output_folder": output_folder
                }

            notify_progress("arxiv_search", f"Found {len(results)} papers! Processing...")

            papers = []
            pdf_count = 0
            abstract_count = 0

            for i, result in enumerate(results):
                # Extract metadata
                metadata = self._extract_paper_metadata(result)
                paper_title = metadata['title'][:60] + "..." if len(metadata['title']) > 60 else metadata['title']

                notify_progress("arxiv_search", f"Processing paper {i+1}/{len(results)}: {paper_title}")

                # Try to download PDF
                pdf_success = False
                pdf_file = None
                abstract_file = None

                notify_progress("arxiv_search", f"[{i+1}/{len(results)}] Downloading PDF from arXiv...")
                pdf_file = self._download_pdf_from_arxiv(result, output_folder)
                if pdf_file:
                    pdf_success = True
                    pdf_count += 1
                    notify_progress("arxiv_search", f"[{i+1}/{len(results)}] ✓ Downloaded PDF successfully")
                else:
                    # Save abstract if PDF download failed
                    notify_progress("arxiv_search", f"[{i+1}/{len(results)}] PDF download failed, saving abstract")
                    abstract_file = self._save_abstract_as_text(metadata, output_folder)
                    abstract_count += 1

                papers.append({
                    "arxiv_id": result.entry_id.split('/')[-1],
                    "title": metadata['title'],
                    "authors": metadata['authors'],
                    "categories": metadata['categories'],
                    "published": metadata['published'],
                    "updated": metadata['updated'],
                    "pdf_url": metadata['pdf_url'],
                    "has_pdf": pdf_success,
                    "pdf_file": pdf_file,
                    "abstract_file": abstract_file,
                    "abstract": metadata['abstract'][:200] + "..." if len(metadata['abstract']) > 200 else metadata['abstract']
                })

                # Be respectful to servers
                time.sleep(0.3)

            # Now save all downloaded files to a collection
            notify_progress("arxiv_search", f"Creating collection '{collection_name}'...")
            collection_result = self._save_to_collection(output_folder, collection_name, user_id, notify_progress)

            if "error" in collection_result:
                notify_progress("arxiv_search", f"Error: {collection_result['error']}")
                return {
                    "success": False,
                    "error": collection_result["error"],
                    "papers_downloaded": len(results),
                    "pdfs_downloaded": pdf_count,
                    "abstracts_saved": abstract_count
                }

            notify_progress("arxiv_search", f"✓ Complete! Downloaded {pdf_count} PDFs, {abstract_count} abstracts. Collection created with {collection_result.get('files_processed')} documents indexed.")

            return {
                "success": True,
                "query": query,
                "total_results": len(results),
                "pdfs_downloaded": pdf_count,
                "abstracts_saved": abstract_count,
                "collection_id": collection_result.get("collection_id"),
                "collection_name": collection_name,
                "files_indexed": collection_result.get("files_processed"),
                "total_chunks": collection_result.get("total_chunks"),
                "papers": papers,
                "message": f"Found {len(results)} papers, downloaded {pdf_count} PDFs and {abstract_count} abstracts. Created collection '{collection_name}' with {collection_result.get('files_processed')} indexed documents."
            }

        except Exception as e:
            notify_progress("arxiv_search", f"Error: {str(e)}")
            return {"error": f"arXiv search failed: {str(e)}"}

    def _extract_paper_metadata(self, result: arxiv.Result) -> Dict[str, Any]:
        """Extract metadata from arXiv result."""
        return {
            'title': result.title,
            'authors': [author.name for author in result.authors],
            'abstract': result.summary,
            'published': result.published.strftime("%Y-%m-%d") if result.published else '',
            'updated': result.updated.strftime("%Y-%m-%d") if result.updated else '',
            'categories': result.categories,
            'primary_category': result.primary_category,
            'pdf_url': result.pdf_url,
            'entry_id': result.entry_id,
            'arxiv_id': result.entry_id.split('/')[-1]
        }

    def _download_pdf_from_arxiv(self, result: arxiv.Result, output_folder: str) -> Optional[str]:
        """Download PDF from arXiv."""
        try:
            arxiv_id = result.entry_id.split('/')[-1]
            # arXiv provides a direct PDF URL
            pdf_url = result.pdf_url

            response = requests.get(pdf_url, timeout=60)
            if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', ''):
                # Sanitize filename
                safe_title = "".join(c for c in result.title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title.replace(' ', '_')
                filename = os.path.join(output_folder, f"arXiv_{arxiv_id}_{safe_title}.pdf")

                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename
        except Exception as e:
            print(f"Error downloading PDF for {result.entry_id}: {e}")
            pass
        return None

    def _save_abstract_as_text(self, metadata: Dict[str, Any], output_folder: str) -> str:
        """Save abstract and metadata as a formatted text file."""
        arxiv_id = metadata['arxiv_id']
        filename = os.path.join(output_folder, f"arXiv_{arxiv_id}_abstract.txt")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"arXiv ID: {arxiv_id}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"TITLE:\n{metadata['title']}\n\n")

            if metadata['authors']:
                f.write(f"AUTHORS:\n{', '.join(metadata['authors'])}\n\n")

            if metadata['published']:
                f.write(f"PUBLISHED: {metadata['published']}")
                if metadata['updated'] and metadata['updated'] != metadata['published']:
                    f.write(f" (Updated: {metadata['updated']})")
                f.write("\n\n")

            if metadata['categories']:
                f.write(f"CATEGORIES:\n{', '.join(metadata['categories'])}\n")
                if metadata.get('primary_category'):
                    f.write(f"Primary: {metadata['primary_category']}\n")
                f.write("\n")

            f.write(f"arXiv URL: https://arxiv.org/abs/{arxiv_id}\n")
            f.write(f"PDF URL: {metadata['pdf_url']}\n\n")

            f.write("ABSTRACT:\n")
            f.write("-" * 80 + "\n")
            f.write(metadata['abstract'] if metadata['abstract'] else "No abstract available")
            f.write("\n" + "-" * 80 + "\n")

        return filename

    def _save_to_collection(self, output_folder: str, collection_name: str, user_id: int,
                            notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
        """Save downloaded files to a new collection."""
        try:
            # Get all files in output folder
            all_files = []
            for root, dirs, files in os.walk(output_folder):
                for file in files:
                    if file.lower().endswith(('.pdf', '.txt')):
                        all_files.append(os.path.join(root, file))

            if not all_files:
                return {"error": "No files to save to collection"}

            if notify_progress:
                notify_progress("arxiv_search", f"Found {len(all_files)} files to process")

            # Import Flask dependencies (already in app context from tool execution)
            from models import Collection, Document, DocumentChunk
            from database import db
            from document_processor import DocumentProcessor
            from vector_store import VectorStore

            # Already in Flask app context, use existing session
            try:
                # Check if collection already exists
                existing = Collection.query.filter_by(name=collection_name, user_id=user_id).first()
                if existing:
                    return {"error": f"Collection '{collection_name}' already exists"}

                if notify_progress:
                    notify_progress("arxiv_search", "Creating collection in database...")

                # Create collection
                collection = Collection(
                    user_id=user_id,
                    name=collection_name,
                    description=f"arXiv papers: {len(all_files)} documents",
                    source_type='arxiv',
                    source_path=output_folder
                )
                db.session.add(collection)
                db.session.flush()

                # Initialize processors
                doc_processor = DocumentProcessor()
                vector_store = VectorStore()

                if notify_progress:
                    notify_progress("arxiv_search", f"Processing and indexing {len(all_files)} documents...")

                # Process all files
                processed_docs = []
                all_chunks = []
                all_chunk_ids = []
                all_metadata = []

                for idx, file_path in enumerate(all_files):
                    try:
                        if notify_progress:
                            filename = os.path.basename(file_path)
                            notify_progress("arxiv_search", f"Indexing document {idx+1}/{len(all_files)}: {filename[:40]}...")

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
                    notify_progress("arxiv_search", f"Adding {len(all_chunks)} chunks to vector store...")

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
        doc_data = doc_processor.process_single_file(file_path)
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

        # Create document record
        document = Document(
            filename=filename,
            file_path=filename,
            stored_file_path=stored_file_path,
            original_file_url=original_file_url,
            content=doc_data['content'],
            summary=doc_data.get('summary', ''),
            file_type=doc_data['file_type'],
            file_size=doc_data['metadata'].get('file_size', 0),
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
