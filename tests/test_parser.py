# tests/test_parser.py - 测试 parser 模块是否正确解析目标页面

from spider import parser
import requests


def test_parse_example_page():
    """
    测试 parser.parse_example_page 能否正确解析示例页面并返回结构化数据
    """
    url = "https://example.com"
    res = requests.get(url, timeout=10)
    html = res.text

    data_list = parser.parse_example_page(html)
    assert isinstance(data_list, list), "Returned data should be a list"

    if data_list:
        sample = data_list[0]
        assert isinstance(sample, dict), "Each item should be a dictionary"
        assert "text" in sample, "Dictionary should contain 'text' key"
        assert "href" in sample, "Dictionary should contain 'href' key"

    print(f"✅ test_parse_example_page passed. Extracted {len(data_list)} items from {url}")


if __name__ == "__main__":
    test_parse_example_page()