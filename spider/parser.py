# spider/parser.py - Quotes to Scrape 专用可执行解析模块

from bs4 import BeautifulSoup

def parse_quotes_page(html, url=None):
    """
    针对 http://quotes.toscrape.com/ 的专用解析函数：
    - 抓取 quote_text（句子）
    - 抓取 author（作者）
    - 抓取 tags（以逗号分隔）
    返回 [{...}, {...}] 可直接写入 DataFrame
    """
    soup = BeautifulSoup(html, 'html.parser')
    records = []

    for quote in soup.find_all("div", class_="quote"):
        quote_text = quote.find("span", class_="text").get_text(strip=True)
        author = quote.find("small", class_="author").get_text(strip=True)
        tags = [tag.get_text(strip=True) for tag in quote.find_all("a", class_="tag")]

        record = {
            "source_url": url if url else "",
            "quote_text": quote_text,
            "author": author,
            "tags": ", ".join(tags)
        }
        records.append(record)

    return records