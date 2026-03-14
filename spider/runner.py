# runner.py - 自动识别解析器 + 分页抓取 + 统一 schema + 去重/增量保存 + 可视化流水线
import os
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from spider import fetcher, parser, utils
from storage.schema import SCHEMA_COLUMNS, normalize_record, prepare_incremental_outputs


os.makedirs("data", exist_ok=True)

def select_parser(url):
    """根据 URL 自动选择对应解析函数。"""
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

def crawl_site(base_url, query: str = ""):
    """
    自动分页抓取 + 自动解析 + 统一 schema + 去重/增量保存 + 自动可视化流水线。
    - query: 可选，记录检索词（用于后续分析/追踪）
    """
    parse_function = select_parser(base_url)
    if parse_function is None:
        print("❌ No available parser, aborting crawl.")
        return

    raw_data = []
    visited = set()
    to_visit = [base_url]

    while to_visit:
        url = to_visit.pop(0)
        if url in visited:
            continue

        print(f"🌐 Crawling: {url}")

        if "api.openalex.org" in urlparse(url).netloc:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"❌ Failed to fetch OpenAlex API, status code: {response.status_code}")
                break
            json_data = response.json()
            page_data = parse_function(json_data, url=url)
            if page_data:
                raw_data.extend(page_data)
                print(f"✅ Extracted {len(page_data)} items from OpenAlex API")
            else:
                print("⚠️ No data extracted from OpenAlex API.")

            next_cursor = json_data.get("meta", {}).get("next_cursor")
            if next_cursor:
                next_url = url.split("?")[0] + "?" + "&".join(
                    [kv for kv in url.split("?")[1].split("&") if not kv.startswith("cursor=")]
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
                raw_data.extend(page_data)
                print(f"✅ Extracted {len(page_data)} items from {url}")
            else:
                print(f"⚠️ No data extracted from {url}")

            soup = BeautifulSoup(html, "html.parser")
            next_page = soup.find("li", class_="next")
            if next_page and next_page.a and next_page.a.get("href"):
                next_url = urljoin(url, next_page.a["href"])
                if next_url not in visited and next_url not in to_visit:
                    to_visit.append(next_url)
            else:
                print("✅ No next page detected, stopping crawl.")

            utils.random_sleep()

        visited.add(url)

    if not raw_data:
        print("❌ No data was collected during this crawl.")
        return

    # === 统一 schema + 去重/增量 ===
    crawled_at_iso = datetime.now(timezone.utc).isoformat()
    normalized_rows = [normalize_record(r, base_url=base_url, crawled_at_iso=crawled_at_iso, query=query) for r in raw_data]
    df_new = pd.DataFrame(normalized_rows, columns=SCHEMA_COLUMNS).drop_duplicates(subset=["uid"])

    domain = urlparse(base_url).netloc.replace(".", "_")
    date_str = utils.get_timestamp(date_only=True)

    master_path = os.path.join("data", f"master_{domain}.csv")
    df_delta, df_master, stats = prepare_incremental_outputs(df_new, master_path)

    # 保存当日新增（delta）
    delta_filename = f"result_{domain}_{date_str}.csv"
    delta_path = os.path.join("data", delta_filename)
    df_delta.to_csv(delta_path, index=False)

    df_master.to_csv(master_path, index=False)

    print(f"\n✅ Crawl completed.")
    print(f"   - New rows today: {stats['new']}")
    print(f"   - Updated rows today: {stats['updated']}")
    print(f"   - Delta rows saved: {len(df_delta)} (saved to {delta_path})")
    print(f"   - Master total unique rows: {len(df_master)} (saved to {master_path})")

    # 自动接入可视化流水线：优先对“当日新增”做分析（更符合增量监测）
    try:
        import analyze_data
        analyze_data.analyze_csv(delta_path)
        print("✅ Visualization pipeline completed (delta file).")
    except Exception as e:
        print(f"⚠️ Visualization pipeline failed: {e}")

    try:
        from pipeline.orchestrator import process_delta_file

        result = process_delta_file(delta_path)
        print(
            f"✅ AI pipeline completed imported={result['imported']} analyzed={result['analyzed']} notified={result['notified']}"
        )
    except Exception as e:
        print(f"⚠️ AI pipeline failed: {e}")

if __name__ == "__main__":
    url = input("Enter the URL to crawl (e.g., https://example.com): ").strip()
    crawl_site(url)
