# auto_runner.py - 定时定点批量科研网站爬取完整代码（直接集成 research-spider 使用）
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import schedule

from spider import runner

# 默认以洛杉矶时间（America/Los_Angeles）触发 03:00 定时任务；如需改时区可修改 TZ 变量
TZ = ZoneInfo("America/Los_Angeles")


def run_crawl_task():
    df_sites = pd.read_csv("config/sites_to_crawl.csv")
    for _, row in df_sites.iterrows():
        if int(row.get("enable", 0)) != 1:
            continue
        url = row["url"]
        now = datetime.now(TZ)
        print(f"\n🚀 [{now}] Starting crawl for {row.get('site_name', 'unknown')} - {url}")
        try:
            runner.crawl_site(url)
        except Exception as e:
            print(f"❌ Error while crawling {row.get('site_name', 'unknown')}: {e}")


def main():
    # 每天凌晨 03:00 自动执行（洛杉矶时间）
    schedule.every().day.at("03:00").do(run_crawl_task)

    print("⏰ auto_runner started. Next runs at 03:00 (America/Los_Angeles).")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
