from typing import Dict, Any, List, Optional, Callable
from .base_tool import BaseTool
import requests
import os
import time
import shutil
import uuid
from pathlib import Path
from urllib.parse import quote, urlencode


class SearchClinicalTrialsTool(BaseTool):
    """Tool for searching ClinicalTrials.gov database."""

    BASE_URL = "https://clinicaltrials.gov/api/v2"
    
    # Valid search fields for clinical trials
    SEARCH_FIELDS = {
        'all': 'Search all fields',
        'condition': 'Medical condition or disease',
        'intervention': 'Treatment or intervention',
        'title': 'Study title',
        'sponsor': 'Study sponsor organization',
        'location': 'Study location (city, state, country)',
        'nctId': 'NCT identifier'
    }
    
    # Study status options
    STUDY_STATUS = {
        'recruiting': 'Currently recruiting participants',
        'not_yet_recruiting': 'Not yet recruiting',
        'completed': 'Study completed',
        'terminated': 'Study terminated',
        'suspended': 'Study suspended',
        'withdrawn': 'Study withdrawn',
        'active_not_recruiting': 'Active, not recruiting'
    }

    def __init__(self):
        self.temp_dir = "temp"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ClinicalTrials-Search-Tool/1.0',
            'Accept': 'application/json'
        })

    def get_name(self) -> str:
        return "search_clinical_trials"

    def get_description(self) -> str:
        return "Search ClinicalTrials.gov database for clinical studies and trials. Results are saved to a new collection. Auto-generates collection name if not provided. Use this when you need to find clinical trials for medical conditions, treatments, or research studies."

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for clinical trials (e.g., 'diabetes treatment', 'cancer immunotherapy', 'Alzheimer disease')"
                },
                "collection_name": {
                    "type": "string",
                    "description": "Optional name for the collection. If not provided, auto-generates as 'clinical_trials_XXX'"
                },
                "search_field": {
                    "type": "string",
                    "description": "Field to search in: 'all', 'condition', 'intervention', 'title', 'sponsor', 'location', 'nctId' (default: 'all')",
                    "default": "all"
                },
                "status": {
                    "type": "string",
                    "description": "Study status filter: 'recruiting', 'completed', 'all' (default: 'all')",
                    "default": "all"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to retrieve (default: 10, max: 100)",
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
            search_field = kwargs.get("search_field", "all")
            status_filter = kwargs.get("status", "all")
            max_results = min(kwargs.get("max_results", 10), 50)

            if not query:
                return {"error": "Query parameter is required"}

            notify_progress("clinical_trials_search", f"Starting Clinical Trials search for: {query[:50]}...")

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
                collection_name = f"clinical_trials_{query_short}_{timestamp}"

            notify_progress("clinical_trials_search", "Preparing search environment...")

            # Clean up temp directory before starting
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

            # Create unique session directory
            session_id = str(int(time.time()))
            output_folder = os.path.join(self.temp_dir, f"clinical_trials_{session_id}")
            Path(output_folder).mkdir(parents=True, exist_ok=True)

            # Search Clinical Trials
            notify_progress("clinical_trials_search", f"Searching ClinicalTrials.gov database (max {max_results} results)...")

            search_results = self._search_clinical_trials(query, search_field, status_filter, max_results)
            

            if not search_results or not search_results.get('studies'):
                notify_progress("clinical_trials_search", "No results found for this query")
                return {
                    "success": True,
                    "message": "No clinical trials found for this query",
                    "results": [],
                    "output_folder": output_folder
                }

            studies = search_results.get('studies', [])[:max_results]
            total_found = len(studies)  # Use actual number of studies returned

            notify_progress("clinical_trials_search", f"Found {total_found} total, processing {len(studies)} studies...")

            # Save results as text files
            saved_count = 0
            items = []

            for i, study in enumerate(studies):
                protocol = study.get('protocolSection', {})
                identification = protocol.get('identificationModule', {})
                title = identification.get('briefTitle', 'No title')[:60]

                notify_progress("clinical_trials_search", f"Processing study {i+1}/{len(studies)}: {title}...")

                # Save study as text file
                text_file = self._save_study_as_text(study, i, output_folder)
                if text_file:
                    saved_count += 1

                # Format item data
                items.append({
                    "nct_id": identification.get('nctId', ''),
                    "title": identification.get('briefTitle', ''),
                    "official_title": identification.get('officialTitle', ''),
                    "phase": self._extract_phase(protocol),
                    "status": self._extract_status(protocol),
                    "conditions": self._extract_conditions(protocol),
                    "interventions": self._extract_interventions(protocol),
                    "sponsor": self._extract_sponsor(protocol),
                    "brief_summary": self._format_brief_summary(self._extract_brief_summary(protocol)),
                    "file": text_file
                })

                # Be respectful to servers
                time.sleep(0.3)

            # Save all files to a collection
            notify_progress("clinical_trials_search", f"Creating collection '{collection_name}'...")
            collection_result = self._save_to_collection(output_folder, collection_name, user_id, notify_progress)

            if "error" in collection_result:
                notify_progress("clinical_trials_search", f"Error: {collection_result['error']}")
                return {
                    "success": False,
                    "error": collection_result["error"],
                    "results_found": len(studies),
                    "results_saved": saved_count
                }

            notify_progress("clinical_trials_search", f"✓ Complete! Saved {saved_count} clinical trials. Collection created with {collection_result.get('files_processed')} documents indexed.")

            return {
                "success": True,
                "query": query,
                "search_field": search_field,
                "status_filter": status_filter,
                "total_found": total_found,
                "total_results": len(studies),
                "results_saved": saved_count,
                "collection_id": collection_result.get("collection_id"),
                "collection_name": collection_name,
                "files_indexed": collection_result.get("files_processed"),
                "total_chunks": collection_result.get("total_chunks"),
                "items": items,
                "next_page_token": search_results.get('nextPageToken'),  # Include pagination token
                "message": f"Retrieved {total_found} clinical trials, saved {saved_count} documents. Created collection '{collection_name}' with {collection_result.get('files_processed')} indexed documents."
            }

        except Exception as e:
            notify_progress("clinical_trials_search", f"Error: {str(e)}")
            return {"error": f"Clinical Trials search failed: {str(e)}"}

    def _search_clinical_trials(self, query: str, search_field: str = "all", 
                               status_filter: str = "all", max_results: int = 10) -> Dict[str, Any]:
        """
        Search Clinical Trials API.

        Args:
            query: Search query string
            search_field: Field to search in
            status_filter: Status filter
            max_results: Maximum number of results

        Returns:
            API response as dictionary
        """
        try:
            # Build query parameters
            params = {
                'pageSize': min(max_results, 100),  # API max is 100
                'format': 'json'
            }

            # Add query based on search field
            if search_field == "all":
                params['query.term'] = query
            elif search_field == "condition":
                params['query.cond'] = query
            elif search_field == "intervention":
                params['query.intr'] = query
            elif search_field == "title":
                params['query.titles'] = query
            elif search_field == "sponsor":
                params['query.spons'] = query
            elif search_field == "location":
                params['query.locn'] = query
            elif search_field == "nctId":
                params['query.id'] = query
            else:
                # Default to general term search
                params['query.term'] = query

            # Add status filter
            if status_filter and status_filter != "all":
                if status_filter == "recruiting":
                    params['filter.overallStatus'] = 'RECRUITING'
                elif status_filter == "completed":
                    params['filter.overallStatus'] = 'COMPLETED'
                elif status_filter == "not_yet_recruiting":
                    params['filter.overallStatus'] = 'NOT_YET_RECRUITING'

            # Construct URL
            url = f"{self.BASE_URL}/studies"
            print(url, params, "constructed url and params")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error during Clinical Trials API request: {e}")
            return {'error': str(e), 'studies': []}

    def _extract_phase(self, protocol: Dict[str, Any]) -> str:
        """Extract study phase from protocol."""
        design = protocol.get('designModule', {})
        phases = design.get('phases', [])
        return ', '.join(phases) if phases else 'N/A'

    def _extract_status(self, protocol: Dict[str, Any]) -> str:
        """Extract study status from protocol."""
        status_module = protocol.get('statusModule', {})
        return status_module.get('overallStatus', 'Unknown')

    def _extract_conditions(self, protocol: Dict[str, Any]) -> List[str]:
        """Extract conditions from protocol."""
        conditions_module = protocol.get('conditionsModule', {})
        return conditions_module.get('conditions', []) if conditions_module else []

    def _extract_interventions(self, protocol: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract interventions from protocol."""
        arms_module = protocol.get('armsInterventionsModule', {})
        if not arms_module:
            return []
        interventions = arms_module.get('interventions', [])
        return [{'type': i.get('type', ''), 'name': i.get('name', '')} for i in interventions if i]

    def _extract_sponsor(self, protocol: Dict[str, Any]) -> str:
        """Extract lead sponsor from protocol."""
        sponsors_module = protocol.get('sponsorCollaboratorsModule', {})
        if not sponsors_module:
            return 'Unknown'
        lead_sponsor = sponsors_module.get('leadSponsor', {})
        return lead_sponsor.get('name', 'Unknown') if lead_sponsor else 'Unknown'

    def _extract_brief_summary(self, protocol: Dict[str, Any]) -> str:
        """Extract brief summary from protocol."""
        description_module = protocol.get('descriptionModule', {})
        return description_module.get('briefSummary', '') if description_module else ''
    
    def _format_brief_summary(self, summary: str) -> str:
        """Format brief summary with length limit."""
        if not summary:
            return ''
        return summary[:200] + "..." if len(summary) > 200 else summary

    def _save_study_as_text(self, study: Dict[str, Any], index: int, output_folder: str) -> str:
        """Save clinical trial study as a formatted text file."""
        protocol = study.get('protocolSection', {})
        identification = protocol.get('identificationModule', {})
        
        nct_id = identification.get('nctId', 'Unknown')
        title = identification.get('briefTitle', 'Untitled Study')

        # Sanitize filename
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        filename = os.path.join(output_folder, f"ClinicalTrial_{index+1}_{nct_id}_{safe_title}.txt")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"CLINICAL TRIAL - {nct_id}\n")
            f.write("=" * 80 + "\n\n")

            # Basic Information
            f.write(f"NCT ID: {nct_id}\n\n")
            f.write(f"BRIEF TITLE:\n{title}\n\n")
            
            official_title = identification.get('officialTitle', '')
            if official_title and official_title != title:
                f.write(f"OFFICIAL TITLE:\n{official_title}\n\n")

            # Study Details
            f.write(f"STUDY PHASE: {self._extract_phase(protocol)}\n")
            f.write(f"STUDY STATUS: {self._extract_status(protocol)}\n\n")

            # Sponsor
            sponsor = self._extract_sponsor(protocol)
            f.write(f"LEAD SPONSOR: {sponsor}\n\n")

            # Conditions
            conditions = self._extract_conditions(protocol)
            if conditions:
                f.write("CONDITIONS STUDIED:\n")
                for condition in conditions:
                    f.write(f"• {condition}\n")
                f.write("\n")

            # Interventions
            interventions = self._extract_interventions(protocol)
            if interventions:
                f.write("INTERVENTIONS:\n")
                for intervention in interventions:
                    f.write(f"• {intervention['type']}: {intervention['name']}\n")
                f.write("\n")

            # Brief Summary
            brief_summary = self._extract_brief_summary(protocol)
            if brief_summary:
                f.write("BRIEF SUMMARY:\n")
                f.write("-" * 80 + "\n")
                f.write(brief_summary)
                f.write("\n" + "-" * 80 + "\n\n")

            # Detailed Description
            description_module = protocol.get('descriptionModule', {})
            detailed_description = description_module.get('detailedDescription', '')
            if detailed_description:
                f.write("DETAILED DESCRIPTION:\n")
                f.write("-" * 80 + "\n")
                f.write(detailed_description)
                f.write("\n" + "-" * 80 + "\n\n")

            # Eligibility
            eligibility_module = protocol.get('eligibilityModule', {})
            if eligibility_module:
                criteria = eligibility_module.get('eligibilityCriteria', '')
                if criteria:
                    f.write("ELIGIBILITY CRITERIA:\n")
                    f.write("-" * 40 + "\n")
                    f.write(criteria)
                    f.write("\n" + "-" * 40 + "\n\n")

                # Age and sex info
                min_age = eligibility_module.get('minimumAge', '')
                max_age = eligibility_module.get('maximumAge', '')
                sex = eligibility_module.get('sex', '')
                healthy_volunteers = eligibility_module.get('healthyVolunteers', False)

                if min_age or max_age or sex:
                    f.write("PARTICIPANT DETAILS:\n")
                    if min_age:
                        f.write(f"Minimum Age: {min_age}\n")
                    if max_age:
                        f.write(f"Maximum Age: {max_age}\n")
                    if sex:
                        f.write(f"Sex: {sex}\n")
                    f.write(f"Healthy Volunteers: {'Yes' if healthy_volunteers else 'No'}\n\n")

            # Contacts and Locations
            contacts_module = protocol.get('contactsLocationsModule', {})
            if contacts_module:
                locations = contacts_module.get('locations', [])
                if locations:
                    f.write("STUDY LOCATIONS:\n")
                    for location in locations[:5]:  # Limit to first 5 locations
                        facility = location.get('facility', '')
                        city = location.get('city', '')
                        state = location.get('state', '')
                        country = location.get('country', '')
                        status = location.get('status', '')
                        
                        location_str = facility
                        if city:
                            # Check if city already contains state info (like "Durham, NC")
                            if state and state not in city:
                                location_str += f", {city}, {state}"
                            else:
                                location_str += f", {city}"
                        elif state:
                            location_str += f", {state}"
                        if country:
                            location_str += f", {country}"
                        if status:
                            location_str += f" ({status})"
                        
                        f.write(f"• {location_str}\n")
                    if len(locations) > 5:
                        f.write(f"... and {len(locations) - 5} more locations\n")
                    f.write("\n")

            # Primary Outcomes
            outcomes_module = protocol.get('outcomesModule', {})
            if outcomes_module:
                primary_outcomes = outcomes_module.get('primaryOutcomes', [])
                if primary_outcomes:
                    f.write("PRIMARY OUTCOMES:\n")
                    for outcome in primary_outcomes[:3]:  # Limit to first 3
                        measure = outcome.get('measure', '')
                        description = outcome.get('description', '')
                        timeframe = outcome.get('timeFrame', '')
                        
                        f.write(f"• {measure}\n")
                        if description:
                            f.write(f"  Description: {description}\n")
                        if timeframe:
                            f.write(f"  Time Frame: {timeframe}\n")
                    f.write("\n")

            f.write("SOURCE: ClinicalTrials.gov\n")
            f.write(f"URL: https://clinicaltrials.gov/study/{nct_id}\n")

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
                notify_progress("clinical_trials_search", f"Found {len(all_files)} files to process")

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
                    notify_progress("clinical_trials_search", "Creating collection in database...")

                # Create collection
                collection = Collection(
                    user_id=user_id,
                    name=collection_name,
                    description=f"Clinical trials from ClinicalTrials.gov: {len(all_files)} studies",
                    source_type='clinical_trials',
                    source_path=output_folder
                )
                db.session.add(collection)
                db.session.flush()

                # Initialize processors
                doc_processor = DocumentProcessor()
                vector_store = VectorStore()

                if notify_progress:
                    notify_progress("clinical_trials_search", f"Processing and indexing {len(all_files)} documents...")

                # Process all files
                processed_docs = []
                all_chunks = []
                all_chunk_ids = []
                all_metadata = []

                for idx, file_path in enumerate(all_files):
                    try:
                        if notify_progress:
                            filename = os.path.basename(file_path)
                            notify_progress("clinical_trials_search", f"Indexing document {idx+1}/{len(all_files)}: {filename[:40]}...")

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
                    notify_progress("clinical_trials_search", f"Adding {len(all_chunks)} chunks to vector store...")

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
