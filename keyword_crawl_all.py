# keyword_crawl_all.py - 单站点合并存储版，实现同一站点分页抓取数据整合到同一个 CSV

import pandas as pd
import os
from datetime import datetime
from urllib.parse import quote
from spider import fetcher, utils
from spider import parser_search

save_folder = "data/keyword_crawl_all"
os.makedirs(save_folder, exist_ok=True)

sites_df = pd.read_csv("config/sites_to_crawl_full.csv")
sites_df = sites_df[sites_df['enable'] == 1]

keyword = input("请输入要抓取的关键词: ").strip()
keyword_encoded = quote(keyword)
today_str = datetime.now().strftime("%Y%m%d")

for idx, row in sites_df.iterrows():
    site_name = row['site_name']
    search_template = row['search_template']
    parser_name = row['parser']

    print(f"\n🚀 正在抓取站点: {site_name}，关键词: {keyword} (全量分页)")

    page = 1
    start = 0
    cursor = "*"
    max_empty_pages = 3
    empty_pages = 0
    all_data = []

    while True:
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
                all_data.extend(page_data)
                print(f"✅ 本页抓取 {len(page_data)} 条，总计 {len(all_data)} 条")
                empty_pages = 0  # 重置
            else:
                print(f"⚠️ 本页无数据。")
                empty_pages += 1

        # 分页推进
        page += 1
        start += 50

        if empty_pages >= max_empty_pages:
            print(f"✅ 连续 {max_empty_pages} 页无数据，停止 {site_name} 抓取。")
            break

    if all_data:
        df = pd.DataFrame(all_data)
        dst_name = f"{site_name}_{keyword.replace(' ', '_')}_{today_str}.csv"
        dst_path = os.path.join(save_folder, dst_name)
        df.to_csv(dst_path, index=False)
        print(f"\n✅ 已合并保存 {len(df)} 条数据至: {dst_path}")
    else:
        print(f"❌ {site_name} 未抓取到任何数据，未生成文件。")

print("\n🎉 所有关键词历史分页抓取并合并完成。")