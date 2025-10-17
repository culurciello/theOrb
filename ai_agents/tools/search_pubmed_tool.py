from typing import Dict, Any, List, Optional, Callable
from .base_tool import BaseTool
from Bio import Entrez
import xml.etree.ElementTree as ET
import requests
import os
import time
import shutil
import uuid
from pathlib import Path


class SearchPubmedTool(BaseTool):
    """Tool for searching PubMed and downloading research papers."""

    def __init__(self):
        # Configure Entrez
        Entrez.email = "euge@purdue.edu"
        Entrez.api_key = "690a6956d93ebe49169007141de9c3a75c08"
        self.temp_dir = "temp"

    def get_name(self) -> str:
        return "search_pubmed"

    def get_description(self) -> str:
        return "Search PubMed for research papers, download PDFs/abstracts, and automatically save them to a new collection. Auto-generates collection name if not provided. Use this when you need to find and organize scientific literature."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for PubMed (e.g., 'cancer therapy', 'COVID-19 vaccine')"
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional name for the collection. If not provided, auto-generates as 'pubmed_search_XXX'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of papers to retrieve (default: 10, max: 50)",
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
            max_results = min(kwargs.get("max_results", 10), 50)

            if not query:
                return {"error": "Query parameter is required"}

            notify_progress("pubmed_search", f"Starting PubMed search for: {query[:50]}...")

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
                collection_name = f"pubmed_search_{query_short}_{timestamp}"

            notify_progress("pubmed_search", "Preparing search environment...")

            # Clean up temp directory before starting
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

            # Create unique session directory
            session_id = str(int(time.time()))
            output_folder = os.path.join(self.temp_dir, f"pubmed_{session_id}")
            Path(output_folder).mkdir(parents=True, exist_ok=True)

            # Search PubMed
            notify_progress("pubmed_search", f"Searching PubMed database (max {max_results} results)...")
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
            record = Entrez.read(handle)
            pmids = record["IdList"]
            handle.close()

            if not pmids:
                notify_progress("pubmed_search", "No papers found for this query")
                return {
                    "success": True,
                    "message": "No papers found for this query",
                    "papers": [],
                    "output_folder": output_folder
                }

            notify_progress("pubmed_search", f"Found {len(pmids)} papers! Fetching details...")

            # Get details for all papers
            xml_data = self._fetch_details(pmids)
            if not xml_data:
                notify_progress("pubmed_search", "Failed to fetch paper details")
                return {"error": "Failed to fetch paper details"}

            notify_progress("pubmed_search", "Parsing paper metadata...")
            root = ET.fromstring(xml_data)
            articles = root.findall(".//PubmedArticle")

            papers = []
            pdf_count = 0
            abstract_count = 0

            for i, article in enumerate(articles):
                pmid = pmids[i]

                # Extract metadata
                metadata = self._extract_paper_metadata(article, pmid)
                paper_title = metadata['title'][:60] + "..." if len(metadata['title']) > 60 else metadata['title']

                notify_progress("pubmed_search", f"Processing paper {i+1}/{len(articles)}: {paper_title}")

                # Try to download PDF
                pdf_success = False
                pdf_file = None
                abstract_file = None

                # 1. Try PMC Open Access
                notify_progress("pubmed_search", f"[{i+1}/{len(articles)}] Checking PMC Open Access...")
                pmc_id = self._get_pmc_id(pmid)
                if pmc_id:
                    pdf_file = self._download_pdf_from_pmc(pmc_id, pmid, output_folder)
                    if pdf_file:
                        pdf_success = True
                        notify_progress("pubmed_search", f"[{i+1}/{len(articles)}] ✓ Downloaded PDF from PMC")

                # 2. Try Unpaywall (open access repository)
                if not pdf_success and metadata['doi']:
                    notify_progress("pubmed_search", f"[{i+1}/{len(articles)}] Checking Unpaywall...")
                    pdf_file = self._try_unpaywall_pdf(metadata['doi'], pmid, output_folder)
                    if pdf_file:
                        pdf_success = True
                        notify_progress("pubmed_search", f"[{i+1}/{len(articles)}] ✓ Downloaded PDF from Unpaywall")

                # 3. If no PDF available, save abstract
                if not pdf_success:
                    notify_progress("pubmed_search", f"[{i+1}/{len(articles)}] PDF not available, saving abstract")
                    abstract_file = self._save_abstract_as_text(metadata, output_folder)
                    abstract_count += 1
                else:
                    pdf_count += 1

                papers.append({
                    "pmid": pmid,
                    "title": metadata['title'],
                    "authors": metadata['authors'],
                    "journal": metadata['journal'],
                    "year": metadata['year'],
                    "doi": metadata['doi'],
                    "has_pdf": pdf_success,
                    "pdf_file": pdf_file,
                    "abstract_file": abstract_file,
                    "abstract": metadata['abstract'][:200] + "..." if len(metadata['abstract']) > 200 else metadata['abstract']
                })

                # Be respectful to servers
                time.sleep(0.5)

            # Now save all downloaded files to a collection
            notify_progress("pubmed_search", f"Creating collection '{collection_name}'...")
            collection_result = self._save_to_collection(output_folder, collection_name, user_id, notify_progress)

            if "error" in collection_result:
                notify_progress("pubmed_search", f"Error: {collection_result['error']}")
                return {
                    "success": False,
                    "error": collection_result["error"],
                    "papers_downloaded": len(pmids),
                    "pdfs_downloaded": pdf_count,
                    "abstracts_saved": abstract_count
                }

            notify_progress("pubmed_search", f"✓ Complete! Downloaded {pdf_count} PDFs, {abstract_count} abstracts. Collection created with {collection_result.get('files_processed')} documents indexed.")

            return {
                "success": True,
                "query": query,
                "total_results": len(pmids),
                "pdfs_downloaded": pdf_count,
                "abstracts_saved": abstract_count,
                "collection_id": collection_result.get("collection_id"),
                "collection_name": collection_name,
                "files_indexed": collection_result.get("files_processed"),
                "total_chunks": collection_result.get("total_chunks"),
                "papers": papers,
                "message": f"Found {len(pmids)} papers, downloaded {pdf_count} PDFs and {abstract_count} abstracts. Created collection '{collection_name}' with {collection_result.get('files_processed')} indexed documents."
            }

        except Exception as e:
            notify_progress("pubmed_search", f"Error: {str(e)}")
            return {"error": f"PubMed search failed: {str(e)}"}

    def _fetch_details(self, id_list):
        """Fetch paper details from PubMed."""
        if not id_list:
            return None
        ids = ",".join(id_list)
        handle = Entrez.efetch(
            db="pubmed",
            id=ids,
            rettype="abstract",
            retmode="xml"
        )
        data = handle.read()
        handle.close()
        return data

    def _get_pmc_id(self, pmid):
        """Convert PubMed ID to PMC ID if available."""
        try:
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid)
            record = Entrez.read(handle)
            handle.close()

            if record[0]["LinkSetDb"]:
                pmc_id = record[0]["LinkSetDb"][0]["Link"][0]["Id"]
                return pmc_id
        except:
            return None
        return None

    def _download_pdf_from_pmc(self, pmc_id, pmid, output_folder):
        """Download PDF from PMC Open Access."""
        try:
            pmc_pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"

            response = requests.get(pmc_pdf_url, timeout=30)
            if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', ''):
                filename = os.path.join(output_folder, f"PMID_{pmid}_PMC_{pmc_id}.pdf")
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename
        except Exception as e:
            pass
        return None

    def _try_unpaywall_pdf(self, doi, pmid, output_folder):
        """Try getting PDF through Unpaywall API (free, legal open access)."""
        if not doi:
            return None

        try:
            url = f"https://api.unpaywall.org/v2/{doi}?email=euge@purdue.edu"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('is_oa') and data.get('best_oa_location'):
                    pdf_url = data['best_oa_location'].get('url_for_pdf')
                    if pdf_url:
                        pdf_response = requests.get(pdf_url, timeout=30)
                        if pdf_response.status_code == 200:
                            filename = os.path.join(output_folder, f"PMID_{pmid}_OA.pdf")
                            with open(filename, 'wb') as f:
                                f.write(pdf_response.content)
                            return filename
        except Exception as e:
            pass
        return None

    def _extract_doi(self, article_xml):
        """Extract DOI from article XML."""
        for article_id in article_xml.findall(".//ArticleId"):
            if article_id.get("IdType") == "doi":
                return article_id.text
        return None

    def _extract_paper_metadata(self, article_xml, pmid):
        """Extract all metadata from article XML."""
        metadata = {
            'pmid': pmid,
            'title': '',
            'authors': [],
            'journal': '',
            'year': '',
            'doi': '',
            'abstract': '',
            'keywords': []
        }

        # Title
        title_elem = article_xml.find(".//ArticleTitle")
        if title_elem is not None:
            metadata['title'] = ''.join(title_elem.itertext())

        # Authors
        for author in article_xml.findall(".//Author"):
            lastname = author.find("LastName")
            forename = author.find("ForeName")
            if lastname is not None and forename is not None:
                metadata['authors'].append(f"{forename.text} {lastname.text}")
            elif lastname is not None:
                metadata['authors'].append(lastname.text)

        # Journal
        journal_elem = article_xml.find(".//Journal/Title")
        if journal_elem is not None:
            metadata['journal'] = journal_elem.text

        # Year
        year_elem = article_xml.find(".//PubDate/Year")
        if year_elem is not None:
            metadata['year'] = year_elem.text
        else:
            medline_date = article_xml.find(".//PubDate/MedlineDate")
            if medline_date is not None:
                metadata['year'] = medline_date.text.split()[0]

        # DOI
        metadata['doi'] = self._extract_doi(article_xml)

        # Abstract
        abstract_parts = []
        for abstract_text in article_xml.findall(".//AbstractText"):
            label = abstract_text.get("Label", "")
            text = ''.join(abstract_text.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        metadata['abstract'] = '\n\n'.join(abstract_parts)

        # Keywords
        for keyword in article_xml.findall(".//Keyword"):
            if keyword.text:
                metadata['keywords'].append(keyword.text)

        return metadata

    def _save_abstract_as_text(self, metadata, output_folder):
        """Save abstract and metadata as a formatted text file."""
        pmid = metadata['pmid']
        filename = os.path.join(output_folder, f"PMID_{pmid}_abstract.txt")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"PMID: {pmid}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"TITLE:\n{metadata['title']}\n\n")

            if metadata['authors']:
                f.write(f"AUTHORS:\n{', '.join(metadata['authors'])}\n\n")

            if metadata['journal']:
                f.write(f"JOURNAL: {metadata['journal']}")
                if metadata['year']:
                    f.write(f" ({metadata['year']})")
                f.write("\n\n")

            if metadata['doi']:
                f.write(f"DOI: {metadata['doi']}\n")
                f.write(f"URL: https://doi.org/{metadata['doi']}\n\n")

            f.write(f"PubMed URL: https://pubmed.ncbi.nlm.nih.gov/{pmid}/\n\n")

            if metadata['keywords']:
                f.write(f"KEYWORDS:\n{', '.join(metadata['keywords'])}\n\n")

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
                notify_progress("pubmed_search", f"Found {len(all_files)} files to process")

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
                    notify_progress("pubmed_search", "Creating collection in database...")

                # Create collection
                collection = Collection(
                    user_id=user_id,
                    name=collection_name,
                    description=f"PubMed papers: {len(all_files)} documents",
                    source_type='pubmed',
                    source_path=output_folder
                )
                db.session.add(collection)
                db.session.flush()

                # Initialize processors
                doc_processor = DocumentProcessor()
                vector_store = VectorStore()

                if notify_progress:
                    notify_progress("pubmed_search", f"Processing and indexing {len(all_files)} documents...")

                # Process all files
                processed_docs = []
                all_chunks = []
                all_chunk_ids = []
                all_metadata = []

                for idx, file_path in enumerate(all_files):
                    try:
                        if notify_progress:
                            filename = os.path.basename(file_path)
                            notify_progress("pubmed_search", f"Indexing document {idx+1}/{len(all_files)}: {filename[:40]}...")

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
                    notify_progress("pubmed_search", f"Adding {len(all_chunks)} chunks to vector store...")

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
