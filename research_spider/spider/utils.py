# spider/utils.py - shared crawler utilities.

import time
import random
import datetime
import os

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "spider_log.txt")

def random_sleep(min_seconds=0.5, max_seconds=1.5):
    duration = random.uniform(min_seconds, max_seconds)
    print(f"💤 Sleeping for {duration:.2f} seconds...")
    time.sleep(duration)

def write_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}\n"
    with open(log_file, "a") as f:
        f.write(log_message)

def get_timestamp(date_only=False):
    """
    Return a timestamp string for filenames and run artifacts.
    - date_only=True returns YYYYMMDD.
    - date_only=False returns YYYYMMDD_HHMMSS.
    """
    if date_only:
        return datetime.datetime.now().strftime("%Y%m%d")
    else:
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
