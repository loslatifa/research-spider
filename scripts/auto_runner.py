# auto_runner.py - scheduled batch crawler entry point for research-spider.
try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # noqa: F401

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import schedule

from research_spider.spider import runner

# Default schedule uses America/Los_Angeles at 03:00; update TZ to change it.
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
    # Run once per day at 03:00 in the configured timezone.
    schedule.every().day.at("03:00").do(run_crawl_task)

    print("⏰ auto_runner started. Next runs at 03:00 (America/Los_Angeles).")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
