# runner.py - parser selection, pagination, schema normalization, and pipeline hooks.
import os
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from research_spider.spider import fetcher, parser, utils
from research_spider.storage.schema import (
    SCHEMA_COLUMNS,
    normalize_record,
    prepare_incremental_outputs,
    summarize_field_completeness,
)


os.makedirs("data", exist_ok=True)

JSON_API_DOMAINS = {
    "api.openalex.org",
    "api.crossref.org",
    "www.ebi.ac.uk",
    "api.semanticscholar.org",
}

def select_parser(url):
    """Select the parser function that matches the URL domain."""
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
    elif "api.crossref.org" in domain:
        return parser.parse_crossref_json
    elif "www.ebi.ac.uk" in domain:
        return parser.parse_europe_pmc_json
    elif "api.semanticscholar.org" in domain:
        return parser.parse_semantic_scholar_json
    else:
        print(f"❌ No parser available for {domain}")
        return None


def _is_json_api_url(url: str) -> bool:
    return urlparse(url).netloc in JSON_API_DOMAINS

def crawl_site(base_url, query: str = ""):
    """
    Crawl paginated content, normalize records, persist deltas, and run downstream hooks.
    - query: optional search term for later analysis and tracing.
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

        if _is_json_api_url(url):
            response = requests.get(url, timeout=20)
            if response.status_code != 200:
                print(f"❌ Failed to fetch JSON API, status code: {response.status_code}")
                break
            json_data = response.json()
            page_data = parse_function(json_data, url=url)
            if page_data:
                raw_data.extend(page_data)
                print(f"✅ Extracted {len(page_data)} items from JSON API")
            else:
                print("⚠️ No data extracted from JSON API.")

            next_cursor = json_data.get("meta", {}).get("next_cursor") if "api.openalex.org" in urlparse(url).netloc else None
            if next_cursor and "?" in url:
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

    # Normalize to the shared schema and compute incremental outputs.
    crawled_at_iso = datetime.now(timezone.utc).isoformat()
    normalized_rows = [normalize_record(r, base_url=base_url, crawled_at_iso=crawled_at_iso, query=query) for r in raw_data]
    df_new = pd.DataFrame(normalized_rows, columns=SCHEMA_COLUMNS).drop_duplicates(subset=["uid"])
    completeness = summarize_field_completeness(df_new)

    domain = urlparse(base_url).netloc.replace(".", "_")
    date_str = utils.get_timestamp(date_only=True)

    master_path = os.path.join("data", f"master_{domain}.csv")
    df_delta, df_master, stats = prepare_incremental_outputs(df_new, master_path)

    # Save the current day's changed records.
    delta_filename = f"result_{domain}_{date_str}.csv"
    delta_path = os.path.join("data", delta_filename)
    df_delta.to_csv(delta_path, index=False)

    df_master.to_csv(master_path, index=False)

    print(f"\n✅ Crawl completed.")
    print(f"   - New rows today: {stats['new']}")
    print(f"   - Updated rows today: {stats['updated']}")
    print(f"   - Delta rows saved: {len(df_delta)} (saved to {delta_path})")
    print(f"   - Master total unique rows: {len(df_master)} (saved to {master_path})")
    print("   - Field completeness:")
    for field, stats in completeness.items():
        print(f"     - {field}: {stats['present']}/{stats['total']} ({stats['rate']:.0%})")

    # Run visualization on the current delta file to focus on newly changed records.
    try:
        from scripts import analyze_data

        analyze_data.analyze_csv(delta_path)
        print("✅ Visualization pipeline completed (delta file).")
    except Exception as e:
        print(f"⚠️ Visualization pipeline failed: {e}")

    try:
        from research_spider.pipeline.orchestrator import process_delta_file

        result = process_delta_file(delta_path)
        print(
            f"✅ AI pipeline completed imported={result['imported']} analyzed={result['analyzed']} notified={result['notified']}"
        )
    except Exception as e:
        print(f"⚠️ AI pipeline failed: {e}")

if __name__ == "__main__":
    url = input("Enter the URL to crawl (e.g., https://example.com): ").strip()
    crawl_site(url)
