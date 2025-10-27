#!/usr/bin/env python3
"""
DOAJ (Directory of Open Access Journals) Search Script

This script provides functionality to search the DOAJ database for articles and journals
using the DOAJ API v4.

API Documentation: https://doaj.org/api/v4/docs
Base URL: https://doaj.org/api/

Features:
- Search for articles and journals
- Filter by various fields (title, ISSN, subject, publisher, etc.)
- Support for pagination
- Export results to JSON or CSV
- Advanced query syntax support

Usage:
    python doaj_search.py --type articles --query "machine learning" --output results.json
    python doaj_search.py --type journals --field subject --query "biology" --page-size 50
"""

import argparse
import json
import csv
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import quote
import requests
from datetime import datetime


class DOAJSearcher:
    """Client for searching the DOAJ API."""

    BASE_URL = "https://doaj.org/api"
    API_VERSION = "v4"

    # Valid search fields for journals
    JOURNAL_FIELDS = {
        'all': 'Search all fields',
        'title': 'Journal title',
        'issn': 'Journal ISSN',
        'publisher': 'Publisher name',
        'license': 'License type',
        'subject': 'Subject area',
        'country': 'Country of publisher'
    }

    # Valid search fields for articles
    ARTICLE_FIELDS = {
        'all': 'Search all fields',
        'title': 'Article title',
        'doi': 'Article DOI',
        'issn': 'Journal ISSN',
        'publisher': 'Publisher name',
        'abstract': 'Article abstract',
        'subject': 'Subject area',
        'author': 'Author name'
    }

    def __init__(self, timeout: int = 30):
        """
        Initialize the DOAJ searcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DOAJ-Search-Script/1.0',
            'Accept': 'application/json'
        })

    def search_articles(
        self,
        query: str,
        field: str = 'all',
        page: int = 1,
        page_size: int = 10,
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for articles in DOAJ.

        Args:
            query: Search query string
            field: Field to search in (default: 'all')
            page: Page number (1-indexed)
            page_size: Number of results per page (max 100)
            sort: Sort field and order (e.g., 'created_date:desc')

        Returns:
            Dictionary containing search results and metadata
        """
        return self._search('articles', query, field, page, page_size, sort)

    def search_journals(
        self,
        query: str,
        field: str = 'all',
        page: int = 1,
        page_size: int = 10,
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for journals in DOAJ.

        Args:
            query: Search query string
            field: Field to search in (default: 'all')
            page: Page number (1-indexed)
            page_size: Number of results per page (max 100)
            sort: Sort field and order (e.g., 'title:asc')

        Returns:
            Dictionary containing search results and metadata
        """
        return self._search('journals', query, field, page, page_size, sort)

    def _search(
        self,
        search_type: str,
        query: str,
        field: str,
        page: int,
        page_size: int,
        sort: Optional[str]
    ) -> Dict[str, Any]:
        """
        Internal method to perform search requests.

        Args:
            search_type: 'articles' or 'journals'
            query: Search query string
            field: Field to search in
            page: Page number
            page_size: Results per page
            sort: Sort parameter

        Returns:
            API response as dictionary
        """
        # Validate page size
        if page_size > 100:
            print("Warning: page_size limited to 100 (DOAJ API maximum)", file=sys.stderr)
            page_size = 100

        # Build the query string based on field
        if field != 'all':
            # Escape special characters in the query
            escaped_query = query.replace('/', r'\/')
            search_query = f"{field}:{escaped_query}"
        else:
            search_query = query

        # Build request parameters - only include pagination and sort
        params = {
            'page': page,
            'pageSize': page_size
        }

        if sort:
            params['sort'] = sort

        # Construct URL with query in the path
        url = f"{self.BASE_URL}/search/{search_type}/{quote(search_query)}"

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during API request: {e}", file=sys.stderr)
            return {'error': str(e), 'results': [], 'total': 0}

    def get_article_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific article by its DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Article data or None if not found
        """
        results = self.search_articles(doi, field='doi', page_size=1)
        if results.get('total', 0) > 0:
            return results['results'][0]
        return None

    def get_journal_by_issn(self, issn: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific journal by its ISSN.

        Args:
            issn: International Standard Serial Number

        Returns:
            Journal data or None if not found
        """
        results = self.search_journals(issn, field='issn', page_size=1)
        if results.get('total', 0) > 0:
            return results['results'][0]
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
    def to_csv(data: Dict[str, Any], output_file: str, search_type: str) -> None:
        """
        Export results to CSV file.

        Args:
            data: Results data to export
            output_file: Output file path
            search_type: 'articles' or 'journals'
        """
        results = data.get('results', [])
        if not results:
            print("No results to export", file=sys.stderr)
            return

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if search_type == 'articles':
                ResultExporter._write_articles_csv(results, f)
            else:
                ResultExporter._write_journals_csv(results, f)

        print(f"Results exported to {output_file}")

    @staticmethod
    def _write_articles_csv(articles: List[Dict], file_obj) -> None:
        """Write articles to CSV."""
        fieldnames = ['title', 'doi', 'authors', 'journal', 'year', 'issn', 'subjects', 'abstract']
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()

        for article in articles:
            bibjson = article.get('bibjson', {})

            # Extract authors
            authors = ', '.join([
                author.get('name', '')
                for author in bibjson.get('author', [])
            ])

            # Extract subjects
            subjects = ', '.join([
                subj.get('term', '')
                for subj in bibjson.get('subject', [])
            ])

            row = {
                'title': bibjson.get('title', ''),
                'doi': ', '.join([id.get('id', '') for id in bibjson.get('identifier', []) if id.get('type') == 'doi']),
                'authors': authors,
                'journal': bibjson.get('journal', {}).get('title', ''),
                'year': bibjson.get('year'),
                'issn': ', '.join(bibjson.get('journal', {}).get('issns', [])),
                'subjects': subjects,
                'abstract': bibjson.get('abstract', '')
            }
            writer.writerow(row)

    @staticmethod
    def _write_journals_csv(journals: List[Dict], file_obj) -> None:
        """Write journals to CSV."""
        fieldnames = ['title', 'issn', 'eissn', 'publisher', 'country', 'subjects', 'apc', 'license']
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()

        for journal in journals:
            bibjson = journal.get('bibjson', {})

            # Extract subjects
            subjects = ', '.join([
                subj.get('term', '')
                for subj in bibjson.get('subject', [])
            ])

            # Extract license
            licenses = ', '.join([
                lic.get('type', '')
                for lic in bibjson.get('license', [])
            ])

            # Extract APC info
            apc_info = bibjson.get('apc', {})
            has_apc = apc_info.get('has_apc', False)
            apc_str = 'Yes' if has_apc else 'No'

            row = {
                'title': bibjson.get('title', ''),
                'issn': bibjson.get('pissn', ''),
                'eissn': bibjson.get('eissn', ''),
                'publisher': bibjson.get('publisher', {}).get('name', ''),
                'country': bibjson.get('publisher', {}).get('country', ''),
                'subjects': subjects,
                'apc': apc_str,
                'license': licenses
            }
            writer.writerow(row)


def print_summary(results: Dict[str, Any], search_type: str) -> None:
    """
    Print a summary of search results.

    Args:
        results: Search results dictionary
        search_type: 'articles' or 'journals'
    """
    total = results.get('total', 0)
    items = results.get('results', [])

    print(f"\n{'='*80}")
    print(f"Search Results: {total} total {search_type} found")
    print(f"Showing {len(items)} results")
    print(f"{'='*80}\n")

    for idx, item in enumerate(items, 1):
        bibjson = item.get('bibjson', {})

        if search_type == 'articles':
            title = bibjson.get('title', 'No title')
            journal = bibjson.get('journal', {}).get('title', 'Unknown journal')
            year = bibjson.get('year', 'N/A')

            # Extract DOI
            doi = next(
                (id.get('id') for id in bibjson.get('identifier', []) if id.get('type') == 'doi'),
                'No DOI'
            )

            print(f"{idx}. {title}")
            print(f"   Journal: {journal} ({year})")
            print(f"   DOI: {doi}")

        else:  # journals
            title = bibjson.get('title', 'No title')
            publisher = bibjson.get('publisher', {}).get('name', 'Unknown publisher')
            issn = bibjson.get('pissn') or bibjson.get('eissn', 'No ISSN')

            print(f"{idx}. {title}")
            print(f"   Publisher: {publisher}")
            print(f"   ISSN: {issn}")

        print()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Search the DOAJ (Directory of Open Access Journals) database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for articles about machine learning
  python doaj_search.py --type articles --query "machine learning"

  # Search for biology journals and export to CSV
  python doaj_search.py --type journals --field subject --query biology --output results.csv

  # Search for a specific DOI
  python doaj_search.py --type articles --field doi --query "10.3389/fpsyg.2013.00479"

  # Get more results with pagination
  python doaj_search.py --type articles --query "climate change" --page 2 --page-size 50

  # Advanced query syntax
  python doaj_search.py --type articles --query "title:(machine AND learning) AND year:2023"
        """
    )

    parser.add_argument(
        '--type',
        choices=['articles', 'journals'],
        default='articles',
        help='Type of content to search (default: articles)'
    )

    parser.add_argument(
        '--query', '-q',
        help='Search query string'
    )

    parser.add_argument(
        '--field', '-f',
        default='all',
        help='Field to search in (use --list-fields to see options)'
    )

    parser.add_argument(
        '--page', '-p',
        type=int,
        default=1,
        help='Page number (default: 1)'
    )

    parser.add_argument(
        '--page-size', '-s',
        type=int,
        default=10,
        help='Number of results per page (max 100, default: 10)'
    )

    parser.add_argument(
        '--sort',
        help='Sort field and order (e.g., "created_date:desc", "title:asc")'
    )

    parser.add_argument(
        '--output', '-o',
        help='Output file path (supports .json and .csv)'
    )

    parser.add_argument(
        '--list-fields',
        action='store_true',
        help='List available search fields and exit'
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
        print("\nAvailable fields for ARTICLES:")
        for field, desc in DOAJSearcher.ARTICLE_FIELDS.items():
            print(f"  {field:15} - {desc}")

        print("\nAvailable fields for JOURNALS:")
        for field, desc in DOAJSearcher.JOURNAL_FIELDS.items():
            print(f"  {field:15} - {desc}")

        return

    # Check if query is provided
    if not args.query:
        print("Error: --query is required for search operations", file=sys.stderr)
        sys.exit(1)

    # Validate field
    valid_fields = DOAJSearcher.ARTICLE_FIELDS if args.type == 'articles' else DOAJSearcher.JOURNAL_FIELDS
    if args.field not in valid_fields:
        print(f"Error: Invalid field '{args.field}' for {args.type}", file=sys.stderr)
        print(f"Valid fields: {', '.join(valid_fields.keys())}", file=sys.stderr)
        sys.exit(1)

    # Initialize searcher
    searcher = DOAJSearcher(timeout=args.timeout)

    # Perform search
    print(f"Searching DOAJ for {args.type}...", file=sys.stderr)

    if args.type == 'articles':
        results = searcher.search_articles(
            query=args.query,
            field=args.field,
            page=args.page,
            page_size=args.page_size,
            sort=args.sort
        )
    else:
        results = searcher.search_journals(
            query=args.query,
            field=args.field,
            page=args.page,
            page_size=args.page_size,
            sort=args.sort
        )

    # Check for errors
    if 'error' in results:
        print(f"Error: {results['error']}", file=sys.stderr)
        sys.exit(1)

    # Print summary unless quiet mode
    if not args.quiet:
        print_summary(results, args.type)

    # Export if output file specified
    if args.output:
        exporter = ResultExporter()

        if args.output.endswith('.json'):
            exporter.to_json(results, args.output)
        elif args.output.endswith('.csv'):
            exporter.to_csv(results, args.output, args.type)
        else:
            print("Error: Output file must be .json or .csv", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
