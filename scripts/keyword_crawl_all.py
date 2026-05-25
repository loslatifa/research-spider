# keyword_crawl_all.py - multi-source keyword crawling with schema normalization.
# Notes:
# 1) Uses search_template entries from config/sites_to_crawl_full.csv and parser_search.
# 2) Normalizes crawl results to the shared schema and deduplicates by uid.
# 3) Maintains data/master_<domain>.csv as the accumulated deduplicated store.
# 4) Writes data/result_<domain>_<YYYYMMDD>_<kw>.csv for the current delta.

try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # noqa: F401

import os
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import pandas as pd
import requests

from research_spider.spider import fetcher
from research_spider.spider import parser, parser_search
from research_spider.storage.schema import (
    SCHEMA_COLUMNS,
    normalize_record,
    prepare_incremental_outputs,
    summarize_field_completeness,
)

os.makedirs("data", exist_ok=True)

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]+", "", s)
    return s[:32] if s else "kw"


def _resolve_parser(parser_name: str):
    return getattr(parser_search, parser_name, None) or getattr(parser, parser_name, None)

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
        openalex_has_next = True

        while True:
            if len(raw_data) >= max_records:
                print(f"✅ 已抓取到上限 {max_records} 条，停止 {site_name} 抓取。")
                break

            url = search_template.format(keyword=keyword_encoded, page=page, start=start, cursor=cursor)
            print(f"🌐 正在抓取: {url}")

            parse_function = _resolve_parser(parser_name)
            if parse_function is None:
                print(f"❌ 未找到解析函数: {parser_name}")
                break

            if parser_name == "parse_openalex_json":
                response = requests.get(url, timeout=20)
                if response.status_code != 200:
                    print(f"⚠️ 跳过 {url}，请求失败，状态码: {response.status_code}")
                    page_data = []
                else:
                    json_data = response.json()
                    page_data = parse_function(json_data, url=url)
                    next_cursor = json_data.get("meta", {}).get("next_cursor")
                    openalex_has_next = bool(next_cursor)
                    cursor = next_cursor or cursor
            else:
                html = fetcher.fetch_url(url)
                if html is None:
                    print(f"⚠️ 跳过 {url}，请求失败。")
                    page_data = []
                else:
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
            if parser_name == "parse_openalex_json" and not openalex_has_next:
                print(f"✅ {site_name} 未返回下一页 cursor，停止抓取。")
                break

        if not raw_data:
            print(f"❌ {site_name} 未抓取到任何数据，未生成文件。")
            continue

        # Normalize to the shared schema and compute incremental outputs.
        crawled_at_iso = datetime.now(timezone.utc).isoformat()
        base_for_source = search_template.split("{")[0]  # Use the static prefix for domain extraction.
        source_domain = urlparse(base_for_source).netloc or site_name
        domain_key = source_domain.replace(".", "_")

        normalized_rows = [normalize_record(r, base_url=base_for_source, crawled_at_iso=crawled_at_iso, query=keyword) for r in raw_data]
        df_new = pd.DataFrame(normalized_rows, columns=SCHEMA_COLUMNS).drop_duplicates(subset=["uid"])
        completeness = summarize_field_completeness(df_new)

        master_path = os.path.join("data", f"master_{domain_key}.csv")
        df_delta, df_master, stats = prepare_incremental_outputs(df_new, master_path)

        delta_path = os.path.join("data", f"result_{domain_key}_{today_str}_{kw_slug}.csv")
        df_delta.to_csv(delta_path, index=False)

        df_master.to_csv(master_path, index=False)

        print(f"\n✅ {site_name} 完成：")
        print(f"   - 新增：{stats['new']} 条")
        print(f"   - 更新：{stats['updated']} 条")
        print(f"   - 本次变更（delta）：{len(df_delta)} 条 -> {delta_path}")
        print(f"   - 累计 master：{len(df_master)} 条 -> {master_path}")
        print("   - 字段完整度：")
        for field, field_stats in completeness.items():
            print(f"     - {field}: {field_stats['present']}/{field_stats['total']} ({field_stats['rate']:.0%})")

        # Run visualization on the current delta file.
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

    print("\n🎉 所有站点关键词抓取完成（统一 schema + master 增量）。")

if __name__ == "__main__":
    main()
