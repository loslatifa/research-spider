# keyword_crawl_all.py - 多站点关键词抓取（统一 schema + 去重 + 增量 master）
# 说明：
# 1) 仍然使用 config/sites_to_crawl_full.csv 中的 search_template + parser_search 解析
# 2) 抓取结果归一到统一 schema，并按 uid 去重
# 3) 每个站点维护 data/master_<domain>.csv（累计去重库）
# 4) 每次运行生成 data/result_<domain>_<YYYYMMDD>_<kw>.csv（本次新增 delta）

import os
import json
import re
import hashlib
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import pandas as pd

from spider import fetcher, utils
from spider import parser_search

os.makedirs("data", exist_ok=True)

# 统一输出 schema（与 runner.py.patched 保持一致）
SCHEMA_COLUMNS = [
    "uid",
    "title",
    "authors",
    "venue",
    "year",
    "date",
    "doi",
    "abstract_url",
    "pdf_url",
    "url",
    "source",
    "query",
    "crawled_at",
    "extra",
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
    s = re.sub(r"^doi:\s*", "", s)
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    return s.strip()

def _make_uid(doi, title, authors, year):
    doi = _norm_doi(doi)
    if doi:
        return "doi:" + doi
    key = "|".join([_norm_text(title).lower(), _norm_text(authors).lower(), _norm_year(year)])
    return "sha1:" + hashlib.sha1(key.encode("utf-8")).hexdigest()

def normalize_record(record: dict, base_url: str, crawled_at_iso: str, query: str) -> dict:
    source = urlparse(base_url).netloc

    # 常见字段兼容（parser_search 输出可能不统一）
    title = record.get("title") or record.get("paper_title") or record.get("quote_text") or ""
    authors = record.get("authors") or record.get("author") or ""
    venue = record.get("journal") or record.get("journal_info") or record.get("venue") or record.get("conference") or ""
    year = record.get("year") or record.get("pub_year") or record.get("publication_year") or ""
    date = record.get("date") or record.get("pub_date") or record.get("publication_date") or ""
    doi = record.get("doi") or record.get("DOI") or record.get("doi_url") or ""
    abstract_url = record.get("abstract_url") or record.get("abstract") or record.get("url") or ""
    pdf_url = record.get("pdf_url") or record.get("fulltext_url") or record.get("pdf") or ""
    url = record.get("url") or record.get("source_url") or abstract_url or ""

    uid = _make_uid(doi, title, authors, year)

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
    return {c: normalized.get(c, "") for c in SCHEMA_COLUMNS}

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

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]+", "", s)
    return s[:32] if s else "kw"

def main():
    sites_df = pd.read_csv("config/sites_to_crawl_full.csv")
    sites_df = sites_df[sites_df["enable"] == 1]

    keyword = input("请输入要抓取的关键词: ").strip()
    if not keyword:
        print("❌ 关键词为空，退出。")
        return

    keyword_encoded = quote(keyword)
    today_str = datetime.now().strftime("%Y%m%d")
    kw_slug = slugify(keyword)

    for _, row in sites_df.iterrows():
        site_name = row["site_name"]
        search_template = row["search_template"]
        parser_name = row["parser"]

        print(f"\n🚀 正在抓取站点: {site_name}，关键词: {keyword} (全量分页，统一 schema)")

        page = 1
        start = 0
        cursor = "*"
        max_empty_pages = 3
        empty_pages = 0
        raw_data = []
        max_records = 2000

        while True:
            if len(raw_data) >= max_records:
                print(f"✅ 已抓取到上限 {max_records} 条，停止 {site_name} 抓取。")
                break

            url = search_template.format(keyword=keyword_encoded, page=page, start=start, cursor=cursor)
            print(f"🌐 正在抓取: {url}")

            html = fetcher.fetch_url(url)
            if html is None:
                print(f"⚠️ 跳过 {url}，请求失败。")
                empty_pages += 1
            else:
                parse_function = getattr(parser_search, parser_name, None)
                if parse_function is None:
                    print(f"❌ 未找到解析函数: {parser_name}")
                    break

                page_data = parse_function(html, url=url)
                if page_data:
                    raw_data.extend(page_data)
                    print(f"✅ 本页抓取 {len(page_data)} 条，总计 {len(raw_data)} 条")
                    empty_pages = 0
                else:
                    print("⚠️ 本页无数据。")
                    empty_pages += 1

            page += 1
            start += 50

            if empty_pages >= max_empty_pages:
                print(f"✅ 连续 {max_empty_pages} 页无数据，停止 {site_name} 抓取。")
                break

        if not raw_data:
            print(f"❌ {site_name} 未抓取到任何数据，未生成文件。")
            continue

        # === 统一 schema + 去重/增量 ===
        crawled_at_iso = datetime.now(timezone.utc).isoformat()
        base_for_source = search_template.split("{")[0]  # 粗略取前缀用于域名提取
        source_domain = urlparse(base_for_source).netloc or site_name
        domain_key = source_domain.replace(".", "_")

        normalized_rows = [normalize_record(r, base_url=base_for_source, crawled_at_iso=crawled_at_iso, query=keyword) for r in raw_data]
        df_new = pd.DataFrame(normalized_rows, columns=SCHEMA_COLUMNS).drop_duplicates(subset=["uid"])

        master_path = os.path.join("data", f"master_{domain_key}.csv")
        existing_uids = _load_existing_uids(master_path)

        df_delta = df_new[~df_new["uid"].isin(existing_uids)].copy()

        delta_path = os.path.join("data", f"result_{domain_key}_{today_str}_{kw_slug}.csv")
        df_delta.to_csv(delta_path, index=False)

        if os.path.exists(master_path):
            try:
                df_master = pd.read_csv(master_path, dtype=str)
            except Exception:
                df_master = pd.DataFrame(columns=SCHEMA_COLUMNS)
        else:
            df_master = pd.DataFrame(columns=SCHEMA_COLUMNS)

        df_master = pd.concat([df_master, df_delta], ignore_index=True).drop_duplicates(subset=["uid"])
        df_master.to_csv(master_path, index=False)

        print(f"\n✅ {site_name} 完成：")
        print(f"   - 本次新增（delta）：{len(df_delta)} 条 -> {delta_path}")
        print(f"   - 累计 master：{len(df_master)} 条 -> {master_path}")

        # 可视化：对本次 delta 分析
        try:
            import analyze_data
            analyze_data.analyze_csv(delta_path)
            print("✅ Visualization pipeline completed (delta file).")
        except Exception as e:
            print(f"⚠️ Visualization pipeline failed: {e}")

    print("\n🎉 所有站点关键词抓取完成（统一 schema + master 增量）。")

if __name__ == "__main__":
    main()
