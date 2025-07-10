# main.py - 集成 robots.txt 自动检查的科研通用爬虫入口

from spider import runner, validator
from spider import robots_checker
import os

if __name__ == "__main__":
    print("\n🚀 Research Spider Framework: Universal Crawler with robots.txt check")
    #url = input("Enter the URL to crawl (e.g., https://example.com): ").strip()
    url = 'http://quotes.toscrape.com/'
    if not url.startswith("http"):
        url = "https://" + url

    # 自动检查 robots.txt
    allowed = robots_checker.can_fetch_url(url)
    if not allowed:
        print("❌ Crawling aborted due to robots.txt disallowing this URL.")
        exit()

    # Crawl and save data
    runner.crawl_site(url)

    # Validate the generated CSV
    output_csv = os.path.join("data", "result.csv")
    validator.validate_csv(output_csv)

    print("\n🎉 Crawling and validation completed. Data ready for analysis.")
