# spider/fetcher.py - 请求封装模块（含防封与随机 sleep）

import requests
import random
import time
from . import utils

# 随机 User-Agent 列表，可自行扩充
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

def fetch_url(url, proxies=None, retries=3, timeout=15):
    """
    请求封装，带随机 UA、可选代理、重试与随机 sleep
    """
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9',
    }
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            if res.status_code == 200:
                utils.random_sleep()
                return res.text
            else:
                print(f"⚠️ Status {res.status_code} on {url}, retrying...")
                time.sleep(random.uniform(0.5,1))
        except Exception as e:
            print(f"⚠️ Exception on {url}: {e}, retrying...")
            time.sleep(random.uniform(5, 10))
    print(f"❌ Failed to fetch {url} after {retries} retries.")
    return None