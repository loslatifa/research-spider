import pandas as pd

from research_spider.spider import runner
from scripts.run_spider import _normalize_url, _resolve_run_options, _select_sites, build_parser


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


def test_smoke_mode_sets_bounded_crawl_and_skips_ai():
    parser = build_parser()
    args = parser.parse_args(["--site", "openalex", "--smoke"])

    options = _resolve_run_options(args)

    assert options["max_pages"] == 1
    assert options["max_items"] == 10
    assert options["run_ai"] is False
    assert options["run_visualization"] is True


def test_explicit_limits_override_smoke_defaults():
    parser = build_parser()
    args = parser.parse_args(["--smoke", "--max-pages", "2", "--max-items", "5", "--no-visualization"])

    options = _resolve_run_options(args)

    assert options["max_pages"] == 2
    assert options["max_items"] == 5
    assert options["run_ai"] is False
    assert options["run_visualization"] is False


def test_fetch_json_api_retries_transient_errors(monkeypatch):
    calls = {"count": 0}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"ok": True}

    def fake_get(url, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary network issue")
        return FakeResponse()

    monkeypatch.setattr(runner.requests, "get", fake_get)
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)

    result = runner._fetch_json_api("https://api.example.test/works", retries=2)

    assert result == {"ok": True}
    assert calls["count"] == 2
