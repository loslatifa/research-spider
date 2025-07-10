# spider/runner.py - 完整自动停止分页抓取版（抓取完所有页自动停止）

import os
import pandas as pd
from . import fetcher, parser, utils
from urllib.parse import urlparse, urljoin

os.makedirs("data", exist_ok=True)

def crawl_site(base_url):
    """
    爬取 base_url，自动递归分页，直到无下一页自动停止，保存 CSV 命名 result_[域名]_[日期].csv
    """
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

        page_data = parser.parse_quotes_page(html, url=url)
        if page_data:
            all_data.extend(page_data)
            print(f"✅ Extracted {len(page_data)} items from {url}")
        else:
            print(f"⚠️ No data extracted from {url}")

        visited.add(url)

        # 自动检测下一页并加入队列
        from bs4 import BeautifulSoup
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