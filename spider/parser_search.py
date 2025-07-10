# parser_search.py - 搜索页面统一解析器集合

from bs4 import BeautifulSoup

#########################################
# 1️⃣ arXiv Search Page (已完成)
#########################################
def parse_arxiv_search_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    results = soup.find_all('li', class_='arxiv-result')
    for result in results:
        title = result.find('p', class_='title is-5 mathjax').get_text(strip=True)
        authors = result.find('p', class_='authors').get_text(strip=True).replace('Authors:', '').strip()
        abstract_url = result.find('p', class_='list-title is-inline-block').find('a')['href']
        pdf_tag = result.find('a', string='pdf')
        pdf_url = 'https://arxiv.org' + pdf_tag['href'] if pdf_tag else ''
        date_tag = result.find('p', class_='is-size-7')
        submitted_date = date_tag.get_text(strip=True).replace('Submitted ', '') if date_tag else ''

        records.append({
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'abstract_url': abstract_url,
            'pdf_url': pdf_url,
            'submitted_date': submitted_date
        })
    return records

#########################################
# 2️⃣ PubMed Search Page
#########################################
def parse_pubmed_search_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    articles = soup.find_all('article', class_='full-docsum')
    for article in articles:
        title_tag = article.find('a', class_='docsum-title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        abstract_url = 'https://pubmed.ncbi.nlm.nih.gov' + title_tag['href'] if title_tag else ''
        authors_tag = article.find('span', class_='docsum-authors full-authors')
        authors = authors_tag.get_text(strip=True) if authors_tag else ''
        journal_tag = article.find('span', class_='docsum-journal-citation full-journal-citation')
        journal_info = journal_tag.get_text(strip=True) if journal_tag else ''

        records.append({
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'journal_info': journal_info,
            'abstract_url': abstract_url
        })
    return records

#########################################
# 3️⃣ DOAJ Search Page
#########################################
def parse_doaj_search_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    articles = soup.find_all('div', class_='search-results-item')
    for article in articles:
        title_tag = article.find('a', class_='title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        abstract_url = 'https://doaj.org' + title_tag['href'] if title_tag else ''
        authors_tag = article.find('div', class_='authors')
        authors = authors_tag.get_text(strip=True) if authors_tag else ''
        journal_tag = article.find('span', class_='journal-title')
        journal_info = journal_tag.get_text(strip=True) if journal_tag else ''

        records.append({
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'journal_info': journal_info,
            'abstract_url': abstract_url
        })
    return records

#########################################
# 4️⃣ IEEE Search Page
#########################################
def parse_ieee_search_page(html, url=None):
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    articles = soup.find_all('div', class_='List-results-items')
    for article in articles:
        title_tag = article.find('h2', class_='result-item-title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        abstract_url_tag = title_tag.find('a') if title_tag else None
        abstract_url = 'https://ieeexplore.ieee.org' + abstract_url_tag['href'] if abstract_url_tag else ''
        authors_tag = article.find('p', class_='author')
        authors = authors_tag.get_text(strip=True) if authors_tag else ''

        pub_date_tag = article.find('div', class_='publisher-info-container')
        pub_date = pub_date_tag.get_text(strip=True) if pub_date_tag else ''

        records.append({
            'source_url': url if url else '',
            'title': title,
            'authors': authors,
            'publication_date': pub_date,
            'abstract_url': abstract_url
        })
    return records