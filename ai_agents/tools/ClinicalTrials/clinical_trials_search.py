#!/usr/bin/env python3
"""
ClinicalTrials.gov Search Script

This script provides functionality to search the ClinicalTrials.gov database for clinical studies
using the ClinicalTrials.gov API v2.

API Documentation: https://clinicaltrials.gov/api/
Base URL: https://clinicaltrials.gov/api/v2

Features:
- Search for clinical trials by condition, intervention, title, sponsor, location
- Filter by study status (recruiting, completed, etc.)
- Support for pagination
- Export results to JSON or CSV
- Comprehensive study information extraction

Usage:
    python clinical_trials_search.py --query "diabetes treatment" --output results.json
    python clinical_trials_search.py --condition "cancer" --status recruiting --page-size 50
"""

import argparse
import json
import csv
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import requests
from datetime import datetime


class ClinicalTrialsSearcher:
    """Client for searching the ClinicalTrials.gov API."""

    BASE_URL = "https://clinicaltrials.gov/api/v2"

    # Valid search fields
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

    def __init__(self, timeout: int = 30):
        """
        Initialize the ClinicalTrials searcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ClinicalTrials-Search-Script/1.0',
            'Accept': 'application/json'
        })

    def search_studies(
        self,
        query: str,
        field: str = 'all',
        status_filter: str = 'all',
        page_size: int = 10,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for clinical trials.

        Args:
            query: Search query string
            field: Field to search in (default: 'all')
            status_filter: Study status filter
            page_size: Number of results per page (max 1000)
            page_token: Token for pagination

        Returns:
            Dictionary containing search results and metadata
        """
        return self._search('studies', query, field, status_filter, page_size, page_token)

    def _search(
        self,
        endpoint: str,
        query: str,
        field: str,
        status_filter: str,
        page_size: int,
        page_token: Optional[str]
    ) -> Dict[str, Any]:
        """
        Internal method to perform search requests.

        Args:
            endpoint: API endpoint (e.g., 'studies')
            query: Search query string
            field: Field to search in
            status_filter: Status filter
            page_size: Results per page
            page_token: Pagination token

        Returns:
            API response as dictionary
        """
        # Validate page size
        if page_size > 1000:
            print("Warning: page_size limited to 1000 (ClinicalTrials API maximum)", file=sys.stderr)
            page_size = 1000

        # Build request parameters
        params = {
            'pageSize': page_size,
            'format': 'json'
        }

        # Add query based on search field
        if field == "all":
            params['query.term'] = query
        elif field == "condition":
            params['query.cond'] = query
        elif field == "intervention":
            params['query.intr'] = query
        elif field == "title":
            params['query.titles'] = query
        elif field == "sponsor":
            params['query.spons'] = query
        elif field == "location":
            params['query.locn'] = query
        elif field == "nctId":
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
            elif status_filter == "terminated":
                params['filter.overallStatus'] = 'TERMINATED'
            elif status_filter == "suspended":
                params['filter.overallStatus'] = 'SUSPENDED'
            elif status_filter == "withdrawn":
                params['filter.overallStatus'] = 'WITHDRAWN'
            elif status_filter == "active_not_recruiting":
                params['filter.overallStatus'] = 'ACTIVE_NOT_RECRUITING'

        # Add pagination token if provided
        if page_token:
            params['pageToken'] = page_token

        # Construct URL
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during API request: {e}", file=sys.stderr)
            return {'error': str(e), 'studies': [], 'totalCount': 0}

    def get_study_by_nct_id(self, nct_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific study by its NCT ID.

        Args:
            nct_id: NCT identifier (e.g., 'NCT12345678')

        Returns:
            Study data or None if not found
        """
        results = self.search_studies(nct_id, field='nctId', page_size=1)
        if results.get('totalCount', 0) > 0:
            return results['studies'][0]
        return None


class ResultExporter:
    """Export search results to various formats."""

    @staticmethod
    def to_json(data: Dict[str, Any], output_file: str, pretty: bool = True) -> None:
        """
        Export results to JSON file.

        Args:
            data: Results data to export
            output_file: Output file path
            pretty: Whether to format JSON with indentation
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)
        print(f"Results exported to {output_file}")

    @staticmethod
    def to_csv(data: Dict[str, Any], output_file: str) -> None:
        """
        Export results to CSV file.

        Args:
            data: Results data to export
            output_file: Output file path
        """
        studies = data.get('studies', [])
        if not studies:
            print("No results to export", file=sys.stderr)
            return

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            ResultExporter._write_studies_csv(studies, f)

        print(f"Results exported to {output_file}")

    @staticmethod
    def _write_studies_csv(studies: List[Dict], file_obj) -> None:
        """Write studies to CSV."""
        fieldnames = [
            'nct_id', 'brief_title', 'official_title', 'phase', 'status', 
            'lead_sponsor', 'conditions', 'interventions', 'enrollment',
            'study_type', 'start_date', 'completion_date', 'locations_count'
        ]
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()

        for study in studies:
            protocol = study.get('protocolSection', {})
            identification = protocol.get('identificationModule', {})
            status_module = protocol.get('statusModule', {})
            design_module = protocol.get('designModule', {})
            sponsors_module = protocol.get('sponsorCollaboratorsModule', {})
            conditions_module = protocol.get('conditionsModule', {})
            arms_module = protocol.get('armsInterventionsModule', {})
            contacts_module = protocol.get('contactsLocationsModule', {})

            # Extract conditions
            conditions = ', '.join(conditions_module.get('conditions', []))

            # Extract interventions
            interventions = []
            for intervention in arms_module.get('interventions', []):
                interventions.append(f"{intervention.get('type', '')}: {intervention.get('name', '')}")
            interventions_str = '; '.join(interventions)

            # Extract lead sponsor
            lead_sponsor = sponsors_module.get('leadSponsor', {}).get('name', '')

            # Extract enrollment
            enrollment_info = design_module.get('enrollmentInfo', {})
            enrollment = enrollment_info.get('count', 'N/A')

            # Extract locations count
            locations = contacts_module.get('locations', [])
            locations_count = len(locations)

            row = {
                'nct_id': identification.get('nctId', ''),
                'brief_title': identification.get('briefTitle', ''),
                'official_title': identification.get('officialTitle', ''),
                'phase': ', '.join(design_module.get('phases', [])),
                'status': status_module.get('overallStatus', ''),
                'lead_sponsor': lead_sponsor,
                'conditions': conditions,
                'interventions': interventions_str,
                'enrollment': enrollment,
                'study_type': design_module.get('studyType', ''),
                'start_date': status_module.get('startDateStruct', {}).get('date', ''),
                'completion_date': status_module.get('completionDateStruct', {}).get('date', ''),
                'locations_count': locations_count
            }
            writer.writerow(row)


def print_summary(results: Dict[str, Any]) -> None:
    """
    Print a summary of search results.

    Args:
        results: Search results dictionary
    """
    total = results.get('totalCount', 0)
    studies = results.get('studies', [])

    print(f"\n{'='*80}")
    print(f"Search Results: {total} total clinical trials found")
    print(f"Showing {len(studies)} results")
    print(f"{'='*80}\n")

    for idx, study in enumerate(studies, 1):
        protocol = study.get('protocolSection', {})
        identification = protocol.get('identificationModule', {})
        status_module = protocol.get('statusModule', {})
        conditions_module = protocol.get('conditionsModule', {})
        sponsors_module = protocol.get('sponsorCollaboratorsModule', {})

        nct_id = identification.get('nctId', 'Unknown')
        title = identification.get('briefTitle', 'No title')
        status = status_module.get('overallStatus', 'Unknown')
        conditions = ', '.join(conditions_module.get('conditions', [])[:3])  # First 3 conditions
        sponsor = sponsors_module.get('leadSponsor', {}).get('name', 'Unknown')

        print(f"{idx}. {title}")
        print(f"   NCT ID: {nct_id}")
        print(f"   Status: {status}")
        print(f"   Conditions: {conditions}")
        print(f"   Sponsor: {sponsor}")
        print()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Search the ClinicalTrials.gov database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for diabetes treatment studies
  python clinical_trials_search.py --query "diabetes treatment"

  # Search for recruiting cancer studies and export to CSV
  python clinical_trials_search.py --condition cancer --status recruiting --output results.csv

  # Search for a specific NCT ID
  python clinical_trials_search.py --nct-id "NCT12345678"

  # Get more results with pagination
  python clinical_trials_search.py --query "heart disease" --page-size 100

  # Search by intervention
  python clinical_trials_search.py --intervention "immunotherapy" --status recruiting
        """
    )

    parser.add_argument(
        '--query', '-q',
        help='General search query string'
    )

    parser.add_argument(
        '--condition', '-c',
        help='Search by medical condition (e.g., "diabetes", "cancer")'
    )

    parser.add_argument(
        '--intervention', '-i',
        help='Search by intervention/treatment (e.g., "immunotherapy", "surgery")'
    )

    parser.add_argument(
        '--title', '-t',
        help='Search in study titles'
    )

    parser.add_argument(
        '--sponsor', '-s',
        help='Search by sponsor organization'
    )

    parser.add_argument(
        '--location', '-l',
        help='Search by study location (city, state, country)'
    )

    parser.add_argument(
        '--nct-id', '-n',
        help='Search by specific NCT ID'
    )

    parser.add_argument(
        '--status',
        choices=['recruiting', 'not_yet_recruiting', 'completed', 'terminated', 
                'suspended', 'withdrawn', 'active_not_recruiting', 'all'],
        default='all',
        help='Filter by study status (default: all)'
    )

    parser.add_argument(
        '--page-size', '-p',
        type=int,
        default=10,
        help='Number of results per page (max 1000, default: 10)'
    )

    parser.add_argument(
        '--page-token',
        help='Page token for pagination (get from previous search)'
    )

    parser.add_argument(
        '--output', '-o',
        help='Output file path (supports .json and .csv)'
    )

    parser.add_argument(
        '--list-fields',
        action='store_true',
        help='List available search fields and status options'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )

    parser.add_argument(
        '--quiet', '-Q',
        action='store_true',
        help='Suppress summary output (useful when exporting)'
    )

    args = parser.parse_args()

    # List fields if requested
    if args.list_fields:
        print("\nAvailable search fields:")
        for field, desc in ClinicalTrialsSearcher.SEARCH_FIELDS.items():
            print(f"  {field:15} - {desc}")

        print("\nAvailable status filters:")
        for status, desc in ClinicalTrialsSearcher.STUDY_STATUS.items():
            print(f"  {status:20} - {desc}")

        return

    # Determine search query and field
    query = None
    field = 'all'

    if args.query:
        query = args.query
        field = 'all'
    elif args.condition:
        query = args.condition
        field = 'condition'
    elif args.intervention:
        query = args.intervention
        field = 'intervention'
    elif args.title:
        query = args.title
        field = 'title'
    elif args.sponsor:
        query = args.sponsor
        field = 'sponsor'
    elif args.location:
        query = args.location
        field = 'location'
    elif args.nct_id:
        query = args.nct_id
        field = 'nctId'

    if not query:
        print("Error: No search query provided. Use one of: --query, --condition, --intervention, --title, --sponsor, --location, --nct-id", file=sys.stderr)
        sys.exit(1)

    # Initialize searcher
    searcher = ClinicalTrialsSearcher(timeout=args.timeout)

    # Perform search
    print(f"Searching ClinicalTrials.gov for {field}: '{query}'...", file=sys.stderr)

    results = searcher.search_studies(
        query=query,
        field=field,
        status_filter=args.status,
        page_size=args.page_size,
        page_token=args.page_token
    )

    # Check for errors
    if 'error' in results:
        print(f"Error: {results['error']}", file=sys.stderr)
        sys.exit(1)

    # Print summary unless quiet mode
    if not args.quiet:
        print_summary(results)

        # Show pagination info
        next_token = results.get('nextPageToken')
        if next_token:
            print(f"Next page token: {next_token}")
            print("Use --page-token to get next page")

    # Export if output file specified
    if args.output:
        exporter = ResultExporter()

        if args.output.endswith('.json'):
            exporter.to_json(results, args.output)
        elif args.output.endswith('.csv'):
            exporter.to_csv(results, args.output)
        else:
            print("Error: Output file must be .json or .csv", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()