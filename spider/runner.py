# runner.py - 自动识别解析器 + 分页抓取 + 统一 schema + 去重/增量保存 + 可视化流水线
import os
import json
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

import pandas as pd
import requests
import re
from bs4 import BeautifulSoup

from spider import fetcher, parser, utils


os.makedirs("data", exist_ok=True)

# 统一输出 schema（缺失允许为空）
SCHEMA_COLUMNS = [
    "uid",          # 去重主键（doi 优先，否则 title+authors+year hash）
    "title",
    "authors",
    "venue",
    "year",
    "date",         # YYYY-MM-DD（若可获得）
    "doi",
    "abstract_url",
    "pdf_url",
    "url",          # 原始条目主链接（若有）
    "source",       # 站点/来源域名
    "query",        # 查询词（若有）
    "crawled_at",   # 抓取时间（ISO）
    "extra",        # 其它字段 JSON 字符串（避免信息丢失）
]

def _norm_text(x):
    if x is None:
        return ""
    return str(x).strip()

def _norm_year(x):
    s = _norm_text(x)
    if not s:
        return ""
    m = re.search(r"(19\d{2}|20\d{2}|2100)", s)
    return m.group(1) if m else s

def _norm_doi(x):
    s = _norm_text(x).lower()
    if not s:
        return ""
    # 简单清洗：去掉 doi: 前缀与 URL 前缀
    s = re.sub(r"^doi:\s*", "", s)
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    return s.strip()

def _make_uid(doi, title, authors, year):
    doi = _norm_doi(doi)
    if doi:
        return "doi:" + doi
    key = "|".join([_norm_text(title).lower(), _norm_text(authors).lower(), _norm_year(year)])
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return "sha1:" + h

def normalize_record(record: dict, base_url: str, crawled_at_iso: str, query: str = "") -> dict:
    source = urlparse(base_url).netloc

    # 常见字段兼容（不同 parser 的列名不一致）
    title = record.get("title") or record.get("paper_title") or record.get("quote_text") or ""
    authors = record.get("authors") or record.get("author") or ""
    venue = record.get("journal") or record.get("journal_info") or record.get("venue") or record.get("conference") or ""
    year = record.get("year") or record.get("pub_year") or record.get("publication_year") or ""
    date = record.get("date") or record.get("pub_date") or record.get("publication_date") or ""
    doi = record.get("doi") or record.get("DOI") or record.get("doi_url") or ""
    abstract_url = record.get("abstract_url") or record.get("abstract") or record.get("url") or ""
    pdf_url = record.get("pdf_url") or record.get("fulltext_url") or record.get("pdf") or ""

    # 条目主链接：优先显式 url，其次 source_url
    url = record.get("url") or record.get("source_url") or abstract_url or ""

    uid = _make_uid(doi, title, authors, year)

    # 把非 schema 字段归档到 extra，避免丢失信息
    extra = {k: v for k, v in record.items() if k not in {
        "title","paper_title","quote_text",
        "authors","author",
        "journal","journal_info","venue","conference",
        "year","pub_year","publication_year",
        "date","pub_date","publication_date",
        "doi","DOI","doi_url",
        "abstract_url","abstract","pdf_url","fulltext_url","pdf",
        "url","source_url",
    }}

    normalized = {
        "uid": uid,
        "title": _norm_text(title),
        "authors": _norm_text(authors),
        "venue": _norm_text(venue),
        "year": _norm_year(year),
        "date": _norm_text(date),
        "doi": _norm_doi(doi),
        "abstract_url": _norm_text(abstract_url),
        "pdf_url": _norm_text(pdf_url),
        "url": _norm_text(url),
        "source": source,
        "query": _norm_text(query),
        "crawled_at": crawled_at_iso,
        "extra": json.dumps(extra, ensure_ascii=False) if extra else "",
    }

    # 补齐列顺序
    return {c: normalized.get(c, "") for c in SCHEMA_COLUMNS}

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

def _load_existing_uids(master_csv_path: str) -> set:
    if not os.path.exists(master_csv_path):
        return set()
    try:
        df = pd.read_csv(master_csv_path, dtype=str)
        if "uid" not in df.columns:
            return set()
        return set(df["uid"].dropna().astype(str).tolist())
    except Exception as e:
        print(f"⚠️ Failed to read master file for incremental dedup: {e}")
        return set()

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
    existing_uids = _load_existing_uids(master_path)

    df_delta = df_new[~df_new["uid"].isin(existing_uids)].copy()

    # 保存当日新增（delta）
    delta_filename = f"result_{domain}_{date_str}.csv"
    delta_path = os.path.join("data", delta_filename)
    df_delta.to_csv(delta_path, index=False)

    # 更新 master（追加增量）
    if os.path.exists(master_path):
        try:
            df_master = pd.read_csv(master_path, dtype=str)
        except Exception:
            df_master = pd.DataFrame(columns=SCHEMA_COLUMNS)
    else:
        df_master = pd.DataFrame(columns=SCHEMA_COLUMNS)

    df_master = pd.concat([df_master, df_delta], ignore_index=True)
    df_master = df_master.drop_duplicates(subset=["uid"])
    df_master.to_csv(master_path, index=False)

    print(f"\n✅ Crawl completed.")
    print(f"   - New unique rows today: {len(df_delta)} (saved to {delta_path})")
    print(f"   - Master total unique rows: {len(df_master)} (saved to {master_path})")

    # 自动接入可视化流水线：优先对“当日新增”做分析（更符合增量监测）
    try:
        import analyze_data
        analyze_data.analyze_csv(delta_path)
        print("✅ Visualization pipeline completed (delta file).")
    except Exception as e:
        print(f"⚠️ Visualization pipeline failed: {e}")

if __name__ == "__main__":
    url = input("Enter the URL to crawl (e.g., https://example.com): ").strip()
    crawl_site(url)
