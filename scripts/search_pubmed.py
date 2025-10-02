# E. Culurciello, October 2025
# API for searching PubMed and downloading PDFs or abstracts
from Bio import Entrez
import xml.etree.ElementTree as ET
import requests
import os
import time
from pathlib import Path

Entrez.email = "euge@purdue.edu"
Entrez.api_key = "690a6956d93ebe49169007141de9c3a75c08"

def fetch_details(id_list):
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

def get_pmc_id(pmid):
    """Convert PubMed ID to PMC ID if available"""
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

def download_pdf_from_pmc(pmc_id, pmid, output_folder):
    """Download PDF from PMC Open Access"""
    try:
        pmc_pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
        
        response = requests.get(pmc_pdf_url, timeout=30)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('content-type', ''):
            filename = os.path.join(output_folder, f"PMID_{pmid}_PMC_{pmc_id}.pdf")
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded PDF: {filename}")
            return True
    except Exception as e:
        print(f"✗ Could not download PMC{pmc_id}: {e}")
    return False

def try_europepmc_pdf(pmid, output_folder):
    """Try downloading from Europe PMC"""
    try:
        url = f"https://europepmc.org/articles/PMC{pmid}?pdf=render"
        response = requests.get(url, timeout=30)
        if response.status_code == 200 and len(response.content) > 1000:
            filename = os.path.join(output_folder, f"PMID_{pmid}_EuropePMC.pdf")
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded PDF from EuropePMC: {filename}")
            return True
    except:
        pass
    return False

def extract_doi(article_xml):
    """Extract DOI from article XML"""
    for article_id in article_xml.findall(".//ArticleId"):
        if article_id.get("IdType") == "doi":
            return article_id.text
    return None

def try_unpaywall_pdf(doi, pmid, output_folder):
    """Try getting PDF through Unpaywall API (free, legal open access)"""
    if not doi:
        return False
    
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
                        print(f"✓ Downloaded PDF from Open Access: {filename}")
                        return True
    except Exception as e:
        pass
    return False

def extract_paper_metadata(article_xml, pmid):
    """Extract all metadata from article XML"""
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
    metadata['doi'] = extract_doi(article_xml)
    
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

def save_abstract_as_text(metadata, output_folder):
    """Save abstract and metadata as a formatted text file"""
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
    
    print(f"✓ Saved abstract: {filename}")
    return True

def search_and_download_papers(query, max_results=10, output_folder="pubmed_papers"):
    """Main function to search PubMed and download available PDFs or abstracts"""
    
    # Create output folder
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Search PubMed
    print(f"Searching PubMed for: '{query}'")
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    pmids = record["IdList"]
    handle.close()
    
    if not pmids:
        print("No PubMed IDs found for this query.")
        return
    
    print(f"Found {len(pmids)} papers. Attempting to download PDFs or abstracts...\n")
    
    # Get details for all papers
    xml_data = fetch_details(pmids)
    if not xml_data:
        return
    
    root = ET.fromstring(xml_data)
    articles = root.findall(".//PubmedArticle")
    
    pdf_count = 0
    abstract_count = 0
    
    for i, article in enumerate(articles):
        pmid = pmids[i]
        
        # Extract metadata
        metadata = extract_paper_metadata(article, pmid)
        
        print(f"\n[{i+1}/{len(pmids)}] PMID: {pmid}")
        print(f"Title: {metadata['title'][:80]}...")
        
        # Try multiple sources for PDF
        pdf_success = False
        
        # 1. Try PMC Open Access
        pmc_id = get_pmc_id(pmid)
        if pmc_id:
            print(f"Found PMC ID: PMC{pmc_id}")
            pdf_success = download_pdf_from_pmc(pmc_id, pmid, output_folder)
        
        # 2. Try Unpaywall (open access repository)
        if not pdf_success and metadata['doi']:
            print(f"Found DOI: {metadata['doi']}")
            pdf_success = try_unpaywall_pdf(metadata['doi'], pmid, output_folder)
        
        # 3. Try Europe PMC
        if not pdf_success:
            pdf_success = try_europepmc_pdf(pmid, output_folder)
        
        # 4. If no PDF available, save abstract
        if pdf_success:
            pdf_count += 1
        else:
            print(f"✗ No open access PDF available - saving abstract instead")
            save_abstract_as_text(metadata, output_folder)
            abstract_count += 1
        
        # Be respectful to servers
        time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"Download complete:")
    print(f"  - PDFs downloaded: {pdf_count}/{len(pmids)}")
    print(f"  - Abstracts saved: {abstract_count}/{len(pmids)}")
    print(f"  - Total papers: {pdf_count + abstract_count}/{len(pmids)}")
    print(f"Papers saved to: {output_folder}/")
    print(f"{'='*60}")

# Run the search and download
if __name__ == "__main__":
    search_and_download_papers(
        query="cancer therapy",
        max_results=10,
        output_folder="pubmed_papers"
    )