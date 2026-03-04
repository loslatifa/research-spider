# run_spider.py - 集成 robots.txt 自动检查的科研通用爬虫入口（对齐统一 schema 输出）
import os
from urllib.parse import urlparse

from spider import runner, validator, robots_checker, utils

def main():
    print("\n🚀 Research Spider Framework: Universal Crawler with robots.txt check")

    url = input("Enter the URL to crawl (e.g., https://example.com): ").strip()
    if not url:
        print("❌ Empty URL, abort.")
        return

    if not url.startswith("http"):
        url = "https://" + url

    # 自动检查 robots.txt
    allowed = robots_checker.can_fetch_url(url)
    if not allowed:
        print("❌ Crawling aborted due to robots.txt disallowing this URL.")
        return

    # Crawl and save data (runner 会生成 data/result_<domain>_<YYYYMMDD>.csv 和 data/master_<domain>.csv)
    runner.crawl_site(url)

    # Validate：优先验证“当天增量 result 文件”；如果找不到则验证 master
    domain_key = urlparse(url).netloc.replace(".", "_")
    date_str = utils.get_timestamp(date_only=True)

    delta_candidate = os.path.join("data", f"result_{domain_key}_{date_str}.csv")
    master_candidate = os.path.join("data", f"master_{domain_key}.csv")

    if os.path.exists(delta_candidate):
        validator.validate_csv(delta_candidate)
    elif os.path.exists(master_candidate):
        validator.validate_csv(master_candidate)
    else:
        print("⚠️ No output CSV found to validate. Please check crawl logs.")

    print("\n🎉 Crawling and validation completed. Data ready for analysis.")

if __name__ == "__main__":
    main()
