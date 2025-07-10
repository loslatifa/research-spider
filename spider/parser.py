# parser.py - 完整包含 quotes、arxiv、pubmed、doaj、ieee 解析模块，可直接用于 research-spider
from bs4 import BeautifulSoup

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
        abs_url = "https://arxiv.org" + abs_link_tag.get('href')
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
        authors_tag = article.find('span', class_='docsum-authors full-authors')
        authors = authors_tag.get_text(strip=True) if authors_tag else ''
        journal_tag = article.find('span', class_='docsum-journal-citation full-journal-citation')
        journal = journal_tag.get_text(strip=True) if journal_tag else ''
        record = {
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'journal': journal,
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
        publication_date = item.get('publication_date', '')
        doi = item.get('doi', '')
        authors = ', '.join([auth['author']['display_name'] for auth in item.get('authorships', [])])
        citation_count = item.get('cited_by_count', 0)
        primary_location = item.get('primary_location') or {}
        source = primary_location.get('source') or {}
        oa_url = source.get('url', '')

        record = {
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'publication_date': publication_date,
            'doi': doi,
            'citation_count': citation_count,
            'openalex_url': oa_url
        }
        records.append(record)

    return records