# runner.py - 完整自动识别解析器、稳定分页抓取并接入可视化流水线版本

import os
import pandas as pd
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import requests
import json

from spider import fetcher, parser, utils

os.makedirs("data", exist_ok=True)

def select_parser(url):
    """
    根据 URL 自动选择对应解析函数。
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
    elif "api.openalex.org" in domain:
        return parser.parse_openalex_json
    else:
        print(f"❌ No parser available for {domain}")
        return None

def crawl_site(base_url):
    """
    自动分页抓取 + 自动解析 + 自动 CSV 保存 + 自动可视化流水线。
    """
    parse_function = select_parser(base_url)
    if parse_function is None:
        print("❌ No available parser, aborting crawl.")
        return

    all_data = []
    visited = set()
    to_visit = [base_url]

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue

        print(f"🌐 Crawling: {url}")

        # 特殊处理 OpenAlex JSON API 抓取
        if "api.openalex.org" in urlparse(url).netloc:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"❌ Failed to fetch OpenAlex API, status code: {response.status_code}")
                break
            json_data = response.json()
            page_data = parse_function(json_data, url=url)
            if page_data:
                all_data.extend(page_data)
                print(f"✅ Extracted {len(page_data)} items from OpenAlex API")
            else:
                print("⚠️ No data extracted from OpenAlex API.")

            next_cursor = json_data.get('meta', {}).get('next_cursor')
            if next_cursor:
                next_url = url.split('?')[0] + '?' + '&'.join(
                    [kv for kv in url.split('?')[1].split('&') if not kv.startswith('cursor=')]
                ) + f"&cursor={next_cursor}"
                if next_url not in visited and next_url not in to_visit:
                    to_visit.append(next_url)
            else:
                print("✅ No next cursor detected, stopping.")
                break

        else:
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

            soup = BeautifulSoup(html, 'html.parser')
            next_page = soup.find('li', class_='next')
            if next_page:
                next_url = urljoin(url, next_page.a['href'])
                if next_url not in visited and next_url not in to_visit:
                    to_visit.append(next_url)
            else:
                print("✅ No next page detected, stopping crawl.")

            utils.random_sleep()

        visited.add(url)

    # 保存 CSV
    if all_data:
        df = pd.DataFrame(all_data)
        domain = urlparse(base_url).netloc.replace('.', '_')
        date_str = utils.get_timestamp(date_only=True)
        csv_filename = f"result_{domain}_{date_str}.csv"
        csv_path = os.path.join("data", csv_filename)
        df.to_csv(csv_path, index=False)
        print(f"\n✅ Crawl completed. Data saved to {csv_path}, total {len(df)} rows.")

        # 自动接入可视化流水线
        try:
            import analyze_data
            analyze_data.analyze_csv(csv_path)
            print("✅ Visualization pipeline completed.")
        except Exception as e:
            print(f"⚠️ Visualization pipeline failed: {e}")

    else:
        print("❌ No data was collected during this crawl.")

if __name__ == "__main__":
    url = input("Enter the URL to crawl (e.g., https://example.com): ").strip()
    crawl_site(url)