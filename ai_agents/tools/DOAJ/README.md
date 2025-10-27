# DOAJ Search Script

A comprehensive Python script for searching the DOAJ (Directory of Open Access Journals) database using their official API v4.

## Features

- Search for both **articles** and **journals**
- Filter by specific fields (title, DOI, ISSN, subject, author, publisher, etc.)
- Support for pagination to retrieve large result sets
- Export results to JSON or CSV formats
- Advanced query syntax support (Boolean operators, field-specific searches)
- Configurable timeouts and result limits
- Clean, formatted output with summaries

## Requirements

- Python 3.6+
- `requests` library

Install dependencies:
```bash
pip install requests
```

## Usage

### Basic Search

Search for articles:
```bash
python doaj_search.py --type articles --query "machine learning"
```

Search for journals:
```bash
python doaj_search.py --type journals --query "biology"
```

### Field-Specific Search

Search for articles by title:
```bash
python doaj_search.py --type articles --field title --query "climate change"
```

Search for articles by DOI:
```bash
python doaj_search.py --type articles --field doi --query "10.3389/fpsyg.2013.00479"
```

Search for journals by subject:
```bash
python doaj_search.py --type journals --field subject --query "computer science"
```

### Pagination

Get more results per page:
```bash
python doaj_search.py --query "open access" --page-size 50
```

Navigate to specific page:
```bash
python doaj_search.py --query "open access" --page 3 --page-size 25
```

### Export Results

Export to JSON:
```bash
python doaj_search.py --query "artificial intelligence" --output results.json
```

Export to CSV:
```bash
python doaj_search.py --query "neuroscience" --output results.csv
```

Quiet mode (suppress console output):
```bash
python doaj_search.py --query "physics" --output results.json --quiet
```

### Advanced Queries

Boolean operators:
```bash
python doaj_search.py --query "machine AND learning"
python doaj_search.py --query "climate OR environment"
```

Complex field-specific queries:
```bash
python doaj_search.py --query "title:(machine learning) AND year:2023"
python doaj_search.py --query "author:Smith AND subject:biology"
```

### List Available Fields

See all searchable fields for articles and journals:
```bash
python doaj_search.py --list-fields
```

## Command-Line Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--type` | | Search type: 'articles' or 'journals' | articles |
| `--query` | `-q` | Search query string | (required) |
| `--field` | `-f` | Field to search in | all |
| `--page` | `-p` | Page number (1-indexed) | 1 |
| `--page-size` | `-s` | Results per page (max 100) | 10 |
| `--sort` | | Sort field and order (e.g., "created_date:desc") | |
| `--output` | `-o` | Output file (.json or .csv) | |
| `--list-fields` | | List available search fields | |
| `--timeout` | | Request timeout in seconds | 30 |
| `--quiet` | `-Q` | Suppress summary output | false |

## Available Search Fields

### For Articles
- `all` - Search all fields
- `title` - Article title
- `doi` - Article DOI
- `issn` - Journal ISSN
- `publisher` - Publisher name
- `abstract` - Article abstract
- `subject` - Subject area
- `author` - Author name

### For Journals
- `all` - Search all fields
- `title` - Journal title
- `issn` - Journal ISSN
- `publisher` - Publisher name
- `license` - License type
- `subject` - Subject area
- `country` - Country of publisher

## Output Formats

### JSON Output
Complete API response including:
- Total number of results
- Page information
- Full metadata for each result
- Timestamp

### CSV Output

**For Articles:**
- Title
- DOI
- Authors
- Journal
- Year
- ISSN
- Subjects
- Abstract

**For Journals:**
- Title
- ISSN
- eISSN
- Publisher
- Country
- Subjects
- APC (Article Processing Charges)
- License

## API Information

- **Base URL:** https://doaj.org/api/
- **API Version:** v4
- **Documentation:** https://doaj.org/api/v4/docs
- **Rate Limits:** No explicit rate limits documented (use responsibly)
- **Authentication:** Not required for public search endpoints

## Examples

### Example 1: Find recent machine learning articles
```bash
python doaj_search.py \
    --type articles \
    --query "machine learning" \
    --page-size 20 \
    --output ml_articles.json
```

### Example 2: Search biology journals in a specific country
```bash
python doaj_search.py \
    --type journals \
    --query "country:US AND subject:biology" \
    --page-size 50 \
    --output us_biology_journals.csv
```

### Example 3: Find articles by a specific author
```bash
python doaj_search.py \
    --type articles \
    --field author \
    --query "Einstein" \
    --page-size 10
```

### Example 4: Retrieve article by DOI
```bash
python doaj_search.py \
    --type articles \
    --field doi \
    --query "10.3389/fpsyg.2013.00479"
```

## Advanced Query Syntax

The DOAJ API uses Elasticsearch query syntax. Some useful patterns:

- **Boolean operators:** `AND`, `OR`, `NOT`
  ```
  "machine AND learning"
  "climate OR environment"
  "biology NOT marine"
  ```

- **Field-specific searches:**
  ```
  "title:covid"
  "author:Smith"
  "year:2023"
  ```

- **Wildcards:**
  ```
  "neur*"  (matches neuroscience, neurology, etc.)
  "bio?"   (matches biol, bios, etc.)
  ```

- **Phrases:**
  ```
  "\"climate change\""
  ```

- **Ranges:**
  ```
  "year:[2020 TO 2023]"
  ```

## Programmatic Usage

You can also use the script as a Python module:

```python
from doaj_search import DOAJSearcher, ResultExporter

# Initialize searcher
searcher = DOAJSearcher(timeout=30)

# Search for articles
results = searcher.search_articles(
    query="machine learning",
    field="all",
    page=1,
    page_size=10
)

# Access results
print(f"Found {results['total']} articles")
for article in results['results']:
    title = article['bibjson']['title']
    print(f"- {title}")

# Export results
exporter = ResultExporter()
exporter.to_json(results, 'output.json')
exporter.to_csv(results, 'output.csv', 'articles')

# Get specific article by DOI
article = searcher.get_article_by_doi("10.3389/fpsyg.2013.00479")

# Get specific journal by ISSN
journal = searcher.get_journal_by_issn("1234-5678")
```

## Error Handling

The script handles various error conditions:
- Network errors and timeouts
- Invalid queries
- API rate limiting
- Invalid field names
- File write errors

Errors are printed to stderr and the script exits with appropriate status codes.

## Notes

- The DOAJ API has a maximum page size of 100 results per request
- For large datasets, use pagination to retrieve all results
- Special characters in queries are automatically escaped
- The script includes a User-Agent header for API requests
- Results are cached in the API for faster repeated queries (15-minute cache)

## Troubleshooting

**Issue:** "404 Not Found" errors
- **Solution:** Check that your query syntax is correct and the API endpoint is accessible

**Issue:** No results found
- **Solution:** Try broadening your search query or searching in 'all' fields instead of specific fields

**Issue:** Timeout errors
- **Solution:** Increase timeout with `--timeout 60` or check your internet connection

**Issue:** CSV export has missing data
- **Solution:** Some fields may not be present in all records. Missing data is left empty in CSV output

## Contributing

Feel free to submit issues or pull requests for improvements.

## License

This script is provided as-is for educational and research purposes.

## Resources

- [DOAJ Website](https://doaj.org/)
- [DOAJ API Documentation](https://doaj.org/api/v4/docs)
- [DOAJ Search Help](https://doaj.org/docs/faq/)
- [Elasticsearch Query Syntax](https://www.elastic.co/guide/en/elasticsearch/reference/1.4/query-dsl-query-string-query.html#query-string-syntax)
