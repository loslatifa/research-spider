# runner.py - 完整自动识别解析器、稳定分页抓取版本

import os
import pandas as pd
from urllib.parse import urlparse, urljoin

from spider import fetcher, parser, utils
from bs4 import BeautifulSoup

# 确保 data 目录存在
os.makedirs("data", exist_ok=True)

def select_parser(url):
    """
    根据输入 URL 自动选择对应解析函数。
    """
    domain = urlparse(url).netloc
    if "quotes.toscrape.com" in domain:
        return parser.parse_quotes_page
    elif "arxiv.org" in domain:
        return parser.parse_arxiv_page
    elif "pubmed.ncbi.nlm.nih.gov" in domain:
        return parser.parse_pubmed_page
    elif "doaj.org" in domain:
        return parser.parse_doaj_page
    elif "ieeexplore.ieee.org" in domain:
        return parser.parse_ieee_page
    else:
        print(f"❌ No parser available for {domain}")
        return None

def crawl_site(base_url):
    """
    自动分页抓取，自动选择解析函数，无下一页自动停止，写入 CSV。
    """
    parse_function = select_parser(base_url)
    if parse_function is None:
        print("❌ No available parser, aborting crawl.")
        return

    all_data = []
    to_visit = [base_url]
    visited = set()

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue

        print(f"🌐 Crawling: {url}")
        html = fetcher.fetch_url(url)
        if html is None:
            print(f"⚠️ Skipping {url} due to fetch error.")
            continue

        page_data = parse_function(html, url=url)
        if page_data:
            all_data.extend(page_data)
            print(f"✅ Extracted {len(page_data)} items from {url}")
        else:
            print(f"⚠️ No data extracted from {url}")

        visited.add(url)

        # 泛化的分页检测逻辑（优先适配 quotes、可在 parse_xxx_page 中补充 next_page_url）
        soup = BeautifulSoup(html, 'html.parser')
        next_page = soup.find('li', class_='next')
        if next_page:
            next_url = urljoin(url, next_page.a['href'])
            if next_url not in visited and next_url not in to_visit:
                to_visit.append(next_url)
        else:
            print("✅ No next page detected. Stopping crawl.")

        utils.random_sleep()

    if all_data:
        df = pd.DataFrame(all_data)
        domain = urlparse(base_url).netloc.replace('.', '_')
        date_str = utils.get_timestamp(date_only=True)
        csv_filename = f"result_{domain}_{date_str}.csv"
        csv_path = os.path.join("data", csv_filename)
        df.to_csv(csv_path, index=False)
        print(f"\n✅ Crawl completed. Data saved to {csv_path}, total {len(df)} rows.")
    else:
        print("❌ No data was collected during this crawl.")

if __name__ == "__main__":
    url = input("Enter the URL to crawl (e.g., https://example.com): ").strip()
    crawl_site(url)