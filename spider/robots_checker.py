
# spider/robots_checker.py - 检查 robots.txt 是否允许爬取目标 URL

import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, urljoin

def can_fetch_url(url, user_agent="*"):
    """
    自动检查 robots.txt 是否允许爬取目标 URL，返回 True / False。
    """
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")

    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        allowed = rp.can_fetch(user_agent, url)
        if allowed:
            print(f"✅ Allowed to crawl {url} as per {robots_url}")
        else:
            print(f"❌ Disallowed to crawl {url} as per {robots_url}")
        return allowed
    except Exception as e:
        print(f"⚠️ Failed to access {robots_url}, assuming allowed. Reason: {e}")
        return True

if __name__ == "__main__":
    test_url = input("Enter URL to check robots.txt permissions: ").strip()
    if not test_url.startswith("http"):
        test_url = "https://" + test_url
    can_fetch_url(test_url)
