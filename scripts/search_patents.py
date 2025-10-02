
# search_patents does nto work on OS X

from patent_client import USApplication, Patent

# Search applications
apps = USApplication.objects.filter(
    first_named_applicant="Tesla"
).order_by('-appl_filing_date')[:10]

# Get patent details
patent = Patent.objects.get('10123456')
print(patent.title)
print(patent.abstract)