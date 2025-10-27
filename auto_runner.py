# auto_runner.py - 定时定点批量科研网站爬取完整代码（直接集成 research-spider 使用）

import pandas as pd
from spider import runner
import time
from datetime import datetime


def run_crawl_task():
    df_sites = pd.read_csv("config/sites_to_crawl.csv")
    for idx, row in df_sites.iterrows():
        if int(row['enable']) != 1:
            continue
        url = row['url']
        print(f"\n🚀 [{datetime.now()}] Starting crawl for {row['site_name']} - {url}")
        try:
            runner.crawl_site(url)
        except Exception as e:
            print(f"❌ Error while crawling {row['site_name']}: {e}")


if __name__ == "__main__":
    while True:
        now = datetime.now()
        # 每天凌晨 03:00 自动执行
        if now.hour == 19 and now.minute == 0:
            run_crawl_task()
            print("✅ All sites crawled, sleeping until next day.")
            time.sleep(60)  # 防抖，避免一分钟内重复执行
        else:
            time.sleep(30)  # 每 30 秒检查一次时间