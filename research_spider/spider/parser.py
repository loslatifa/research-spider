# parser.py - parsers for quotes, arXiv, PubMed, DOAJ, IEEE, and JSON paper APIs.
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from research_spider.storage.schema import reconstruct_openalex_abstract


def _last_url_segment(value: str) -> str:
    path = urlparse(value or '').path.strip('/')
    return path.rsplit('/', 1)[-1] if path else ''


def parse_quotes_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    for quote in soup.find_all("div", class_="quote"):
        quote_text = quote.find("span", class_="text").get_text(strip=True)
        author = quote.find("small", class_="author").get_text(strip=True)
        tags = [tag.get_text(strip=True) for tag in quote.find_all("a", class_="tag")]
        record = {
            "source_url": url if url else "",
            "quote_text": quote_text,
            "author": author,
            "tags": ", ".join(tags)
        }
        records.append(record)
    return records

def parse_arxiv_page(html, url=None):
    soup = BeautifulSoup(html, "html.parser")
    records = []
    dl = soup.find('dl')
    if not dl:
        return records
    dt_tags = dl.find_all('dt')
    dd_tags = dl.find_all('dd')
    for dt, dd in zip(dt_tags, dd_tags):
        abs_link_tag = dt.find('a', title='Abstract')
        if not abs_link_tag:
            continue
        abs_url = urljoin("https://arxiv.org", abs_link_tag.get('href'))
        arxiv_id = _last_url_segment(abs_url)
        pdf_url = abs_url.replace('/abs/', '/pdf/')
        title_tag = dd.find('div', class_='list-title mathjax')
        title = title_tag.get_text(strip=True).replace('Title:', '') if title_tag else ''
        authors_tag = dd.find('div', class_='list-authors')
        authors = ''
        if authors_tag:
            authors_list = authors_tag.find_all('a')
            authors = ', '.join(a.get_text(strip=True) for a in authors_list)
        record = {
            "source_url": url if url else "",
            "title": title,
            "authors": authors,
            "abstract": "",
            "keywords": "",
            "arxiv_id": arxiv_id,
            "abstract_url": abs_url,
            "pdf_url": pdf_url
        }
        records.append(record)
    return records

def parse_pubmed_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    for article in soup.find_all('article', class_='full-docsum'):
        title_tag = article.find('a', class_='docsum-title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        href = 'https://pubmed.ncbi.nlm.nih.gov' + title_tag['href'] if title_tag else ''
        pmid_match = re.search(r'/(\d+)/?$', href)
        pmid = pmid_match.group(1) if pmid_match else ''
        authors_tag = article.find('span', class_='docsum-authors full-authors')
        authors = authors_tag.get_text(strip=True) if authors_tag else ''
        journal_tag = article.find('span', class_='docsum-journal-citation full-journal-citation')
        journal = journal_tag.get_text(strip=True) if journal_tag else ''
        record = {
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'journal': journal,
            'pmid': pmid,
            'url': href
        }
        records.append(record)
    return records

def parse_doaj_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    for article in soup.find_all('div', class_='search-result-item'):
        title_tag = article.find('a')
        title = title_tag.get_text(strip=True) if title_tag else ''
        href = 'https://doaj.org' + title_tag['href'] if title_tag else ''
        authors_tag = article.find('div', class_='item-authors')
        authors = authors_tag.get_text(strip=True) if authors_tag else ''
        record = {
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'url': href
        }
        records.append(record)
    return records

def parse_ieee_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    for article in soup.find_all('div', class_='List-results-items'):
        title_tag = article.find('h2', class_='result-item-title')
        title_link = title_tag.find('a') if title_tag else None
        title = title_link.get_text(strip=True) if title_link else ''
        href = 'https://ieeexplore.ieee.org' + title_link['href'] if title_link and title_link.has_attr('href') else ''
        authors_tag = article.find('p', class_='author')
        authors = authors_tag.get_text(strip=True) if authors_tag else ''
        record = {
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'url': href
        }
        records.append(record)
    return records

def parse_openalex_json(json_data, url=None):
    records = []
    for item in json_data.get('results', []):
        title = item.get('title', '')
        openalex_id = item.get('id', '')
        publication_date = item.get('publication_date', '')
        doi = item.get('doi', '')
        publication_year = item.get('publication_year', '')
        authors = ', '.join([auth['author']['display_name'] for auth in item.get('authorships', [])])
        citation_count = item.get('cited_by_count', 0)
        primary_location = item.get('primary_location') or {}
        source = primary_location.get('source') or {}
        venue = source.get('display_name', '')
        landing_page_url = primary_location.get('landing_page_url', '')
        pdf_url = primary_location.get('pdf_url', '')
        abstract = reconstruct_openalex_abstract(item.get('abstract_inverted_index') or {})
        keywords = ', '.join(concept.get('display_name', '') for concept in item.get('concepts', []) if concept.get('display_name'))

        record = {
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'venue': venue,
            'publication_year': publication_year,
            'publication_date': publication_date,
            'doi': doi,
            'openalex_id': openalex_id,
            'abstract': abstract,
            'keywords': keywords,
            'abstract_url': landing_page_url,
            'pdf_url': pdf_url,
            'url': openalex_id or landing_page_url,
            'citation_count': citation_count,
            'openalex_url': source.get('url', '')
        }
        records.append(record)

    return records


def parse_crossref_json(json_data, url=None):
    records = []
    for item in json_data.get('message', {}).get('items', []):
        title = ' '.join(item.get('title') or [])
        abstract = item.get('abstract', '')
        authors = ', '.join(
            ' '.join(part for part in [author.get('given', ''), author.get('family', '')] if part).strip()
            for author in item.get('author', [])
        )
        published = item.get('published-print') or item.get('published-online') or item.get('created') or {}
        date_parts = published.get('date-parts') or []
        date_values = date_parts[0] if date_parts else []
        year = str(date_values[0]) if date_values else ''
        date = '-'.join(str(part) for part in date_values) if date_values else ''
        venue = ', '.join(item.get('container-title') or [])
        doi = item.get('DOI', '')
        record = {
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'venue': venue,
            'publication_year': year,
            'publication_date': date,
            'doi': doi,
            'abstract': abstract,
            'url': item.get('URL', ''),
            'crossref_type': item.get('type', ''),
            'citation_count': item.get('is-referenced-by-count', 0),
        }
        records.append(record)
    return records


def parse_europe_pmc_json(json_data, url=None):
    records = []
    for item in json_data.get('resultList', {}).get('result', []):
        doi = item.get('doi', '')
        pmid = item.get('pmid', '')
        pmcid = item.get('pmcid', '')
        source_id = ''
        if pmid:
            source_id = f'pmid:{pmid}'
        elif pmcid:
            source_id = f'europepmc:{pmcid.lower()}'
        elif item.get('id'):
            source_id = f'europepmc:{item.get("id", "").lower()}'
        record = {
            'source_url': url if url else '',
            'title': item.get('title', ''),
            'authors': item.get('authorString', ''),
            'venue': item.get('journalTitle', ''),
            'publication_year': item.get('pubYear', ''),
            'publication_date': item.get('firstPublicationDate') or item.get('pubYear', ''),
            'doi': doi,
            'pmid': pmid,
            'source_id': source_id,
            'abstract': item.get('abstractText', ''),
            'keywords': item.get('keywordList', {}).get('keyword', ''),
            'url': item.get('fullTextUrlList', {}).get('fullTextUrl', [{}])[0].get('url', '') if item.get('fullTextUrlList') else '',
            'europe_pmc_id': item.get('id', ''),
        }
        records.append(record)
    return records


def parse_semantic_scholar_json(json_data, url=None):
    records = []
    for item in json_data.get('data', []):
        external_ids = item.get('externalIds') or {}
        authors = ', '.join(author.get('name', '') for author in item.get('authors', []))
        open_access_pdf = item.get('openAccessPdf') or {}
        semantic_scholar_id = item.get('paperId', '')
        record = {
            'source_url': url if url else '',
            'title': item.get('title', ''),
            'authors': authors,
            'venue': item.get('venue', ''),
            'publication_year': item.get('year', ''),
            'publication_date': item.get('publicationDate', ''),
            'doi': external_ids.get('DOI', ''),
            'pmid': external_ids.get('PubMed', ''),
            'arxiv_id': external_ids.get('ArXiv', ''),
            'source_id': f'semanticscholar:{semantic_scholar_id.lower()}' if semantic_scholar_id else '',
            'abstract': item.get('abstract', ''),
            'abstract_url': item.get('url', ''),
            'pdf_url': open_access_pdf.get('url', ''),
            'url': item.get('url', ''),
            'semantic_scholar_id': semantic_scholar_id,
        }
        records.append(record)
    return records
