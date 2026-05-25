import pandas as pd

from scripts.run_spider import _normalize_url, _select_sites


def test_normalize_url_adds_https_when_missing():
    assert _normalize_url("example.com") == "https://example.com"
    assert _normalize_url("https://example.com") == "https://example.com"


def test_select_sites_defaults_to_enabled_rows():
    df = pd.DataFrame(
        [
            {"site_name": "arxiv", "url": "https://arxiv.org", "enable": "1"},
            {"site_name": "pubmed", "url": "https://pubmed.ncbi.nlm.nih.gov", "enable": "0"},
        ]
    )

    selected = _select_sites(df, [])

    assert len(selected) == 1
    assert selected[0]["site_name"] == "arxiv"


def test_select_sites_filters_by_site_name_case_insensitively():
    df = pd.DataFrame(
        [
            {"site_name": "arxiv", "url": "https://arxiv.org", "enable": 1},
            {"site_name": "pubmed", "url": "https://pubmed.ncbi.nlm.nih.gov", "enable": 1},
        ]
    )

    selected = _select_sites(df, ["PubMed"])

    assert len(selected) == 1
    assert selected[0]["site_name"] == "pubmed"
