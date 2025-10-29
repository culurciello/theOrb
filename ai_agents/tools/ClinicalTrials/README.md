# Clinical Trials Search Tool

This directory contains a standalone command-line tool for searching the ClinicalTrials.gov database using their API v2.

## Overview

The ClinicalTrials.gov database contains information about clinical studies conducted around the world. This tool provides a convenient way to search for clinical trials by various criteria including medical conditions, interventions, sponsors, and more.

## API Information

- **Base URL**: https://clinicaltrials.gov/api/v2
- **Endpoint**: /studies
- **Documentation**: https://clinicaltrials.gov/api/
- **Authentication**: None required (public API)

## Features

- Search by multiple criteria (condition, intervention, title, sponsor, location, NCT ID)
- Filter by study status (recruiting, completed, terminated, etc.)
- Pagination support with page tokens
- Export results to JSON or CSV formats
- Comprehensive study information extraction
- Command-line interface with extensive options

## Usage

### Basic Examples

```bash
# Search for diabetes treatment studies
python clinical_trials_search.py --query "diabetes treatment"

# Search for recruiting cancer studies
python clinical_trials_search.py --condition cancer --status recruiting

# Search for a specific NCT ID
python clinical_trials_search.py --nct-id "NCT12345678"

# Search by intervention
python clinical_trials_search.py --intervention "immunotherapy" --status recruiting
```

### Advanced Usage

```bash
# Get more results with larger page size
python clinical_trials_search.py --query "heart disease" --page-size 100

# Export results to CSV
python clinical_trials_search.py --condition "diabetes" --output results.csv

# Export to JSON with quiet mode (no console output)
python clinical_trials_search.py --query "cancer immunotherapy" --output results.json --quiet

# Search by sponsor organization
python clinical_trials_search.py --sponsor "Pfizer" --status recruiting
```

### Pagination

The ClinicalTrials.gov API uses token-based pagination:

```bash
# First search
python clinical_trials_search.py --query "diabetes" --page-size 50

# Use the returned page token for next page
python clinical_trials_search.py --query "diabetes" --page-size 50 --page-token "TOKEN_FROM_PREVIOUS_SEARCH"
```

## Command Line Options

- `--query, -q`: General search query string
- `--condition, -c`: Search by medical condition
- `--intervention, -i`: Search by intervention/treatment
- `--title, -t`: Search in study titles
- `--sponsor, -s`: Search by sponsor organization
- `--location, -l`: Search by study location
- `--nct-id, -n`: Search by specific NCT ID
- `--status`: Filter by study status (recruiting, completed, etc.)
- `--page-size, -p`: Number of results per page (max 1000, default 10)
- `--page-token`: Page token for pagination
- `--output, -o`: Output file path (.json or .csv)
- `--list-fields`: List available search fields and status options
- `--timeout`: Request timeout in seconds (default 30)
- `--quiet, -Q`: Suppress summary output

## Search Fields

- **all**: Search all fields (default)
- **condition**: Medical condition or disease
- **intervention**: Treatment or intervention
- **title**: Study title
- **sponsor**: Study sponsor organization
- **location**: Study location (city, state, country)
- **nctId**: NCT identifier

## Study Status Options

- **recruiting**: Currently recruiting participants
- **not_yet_recruiting**: Not yet recruiting
- **completed**: Study completed
- **terminated**: Study terminated
- **suspended**: Study suspended
- **withdrawn**: Study withdrawn
- **active_not_recruiting**: Active, not recruiting
- **all**: All statuses (default)

## Output Formats

### JSON Format
Exports the complete API response including all study details, metadata, and pagination information.

### CSV Format
Exports a simplified table with key study information:
- NCT ID
- Brief Title
- Official Title
- Phase
- Status
- Lead Sponsor
- Conditions
- Interventions
- Enrollment
- Study Type
- Start Date
- Completion Date
- Locations Count

## Integration with theOrb

This CLI tool serves as a companion to the main `SearchClinicalTrialsTool` integrated into theOrb's agent system. While the agent tool provides seamless integration with theOrb's collection system and vector store, this CLI tool offers:

- Standalone operation outside of theOrb
- Direct API access for testing and debugging
- Batch processing capabilities
- Export functionality for external analysis

## Requirements

- Python 3.11+
- requests library
- No additional dependencies beyond Python standard library

## Error Handling

The tool includes comprehensive error handling for:
- Network timeouts and connection errors
- API rate limiting
- Invalid search parameters
- File I/O errors during export
- Malformed API responses

## Rate Limiting

The ClinicalTrials.gov API does not specify explicit rate limits, but the tool includes:
- Configurable timeout settings
- Proper User-Agent headers
- Respectful request patterns

## Examples Output

### Summary Output
```
================================================================================
Search Results: 1,247 total clinical trials found
Showing 10 results
================================================================================

1. Diabetes Treatment with Novel Drug X
   NCT ID: NCT12345678
   Status: RECRUITING
   Conditions: Type 2 Diabetes Mellitus, Insulin Resistance
   Sponsor: Example Pharmaceutical Company

2. Comparison of Diabetes Medications
   NCT ID: NCT87654321
   Status: COMPLETED
   Conditions: Type 1 Diabetes Mellitus
   Sponsor: University Medical Center
...
```

### CSV Export Sample
```csv
nct_id,brief_title,official_title,phase,status,lead_sponsor,conditions,interventions,...
NCT12345678,"Diabetes Treatment Study","A Phase 3 Study of...","PHASE3","RECRUITING","Pharma Corp","Type 2 Diabetes","Drug: Novel Agent X",...
```