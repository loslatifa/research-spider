try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # noqa: F401

import argparse
import os
from typing import Iterable, List
from urllib.parse import urlparse

import pandas as pd

from research_spider.spider import robots_checker, runner, utils, validator


DEFAULT_SITES_CONFIG = "config/sites_to_crawl.csv"


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    return url if url.startswith("http") else f"https://{url}"


def _load_sites(config_path: str) -> pd.DataFrame:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    df = pd.read_csv(config_path)
    required_columns = {"site_name", "url", "enable"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns in {config_path}: {sorted(missing_columns)}")
    return df


def _select_sites(df_sites: pd.DataFrame, site_names: Iterable[str]) -> List[dict]:
    if site_names:
        requested = {name.strip().lower() for name in site_names if name.strip()}
        filtered = df_sites[df_sites["site_name"].astype(str).str.lower().isin(requested)]
    else:
        enabled = pd.to_numeric(df_sites["enable"], errors="coerce").fillna(0).astype(int)
        filtered = df_sites[enabled == 1]
    return filtered.to_dict(orient="records")


def _validate_latest_output(url: str) -> None:
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


def _resolve_run_options(args: argparse.Namespace) -> dict:
    max_pages = args.max_pages
    max_items = args.max_items
    run_ai = not args.no_ai
    run_visualization = not args.no_visualization
    if args.smoke:
        max_pages = max_pages or 1
        max_items = max_items or 10
        run_ai = False
    return {
        "max_pages": max_pages,
        "max_items": max_items,
        "run_ai": run_ai,
        "run_visualization": run_visualization,
    }


def _crawl_url(
    url: str,
    site_name: str = "manual",
    max_pages: int = 0,
    max_items: int = 0,
    run_ai: bool = True,
    run_visualization: bool = True,
) -> None:
    normalized_url = _normalize_url(url)
    if not normalized_url:
        print(f"❌ Empty URL for site={site_name}, skipping.")
        return

    print(f"\n🚀 Crawling site={site_name} url={normalized_url}")
    allowed = robots_checker.can_fetch_url(normalized_url)
    if not allowed:
        print(f"❌ Crawling aborted for {site_name}: robots.txt disallows this URL.")
        return

    runner.crawl_site(
        normalized_url,
        max_pages=max_pages,
        max_items=max_items,
        run_ai=run_ai,
        run_visualization=run_visualization,
    )
    _validate_latest_output(normalized_url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run research spider using configured common sources or a manual URL."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_SITES_CONFIG,
        help="Path to crawl source config CSV.",
    )
    parser.add_argument(
        "--site",
        action="append",
        dest="site_names",
        help="Specific site_name from config to crawl. Can be passed multiple times.",
    )
    parser.add_argument(
        "--url",
        help="Manual URL override. When provided, config selection is skipped.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List configured sources and exit.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Maximum pages/API cursor pages to crawl. 0 means unlimited.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=0,
        help="Maximum records to keep from the crawl. 0 means unlimited.",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI analysis and digest notification after writing crawl outputs.",
    )
    parser.add_argument(
        "--no-visualization",
        action="store_true",
        help="Skip local visualization generation after writing crawl outputs.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a quick smoke test: max 1 page, max 10 items, skip AI.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_options = _resolve_run_options(args)

    print("\n🚀 Research Spider Framework: Config-driven crawler")

    if args.url:
        _crawl_url(
            args.url,
            **run_options,
        )
        print("\n🎉 Crawling and validation completed. Data ready for analysis.")
        return

    df_sites = _load_sites(args.config)

    if args.list:
        print(df_sites[["site_name", "url", "enable"]].to_string(index=False))
        return

    selected_sites = _select_sites(df_sites, args.site_names or [])
    if not selected_sites:
        if args.site_names:
            print(f"❌ No matching sites found in config: {args.site_names}")
        else:
            print("❌ No enabled sites found in config.")
        return

    for site in selected_sites:
        try:
            _crawl_url(
                site["url"],
                site_name=str(site.get("site_name", "unknown")),
                **run_options,
            )
        except Exception as exc:
            print(f"❌ Error while crawling {site.get('site_name', 'unknown')}: {exc}")

    print("\n🎉 Crawling and validation completed. Data ready for analysis.")


if __name__ == "__main__":
    main()
