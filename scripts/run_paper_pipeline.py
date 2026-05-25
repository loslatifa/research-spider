try:
    from scripts import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import _bootstrap  # noqa: F401

import argparse
import glob
import os

from research_spider.pipeline.orchestrator import process_delta_files


def _find_latest_delta_files(limit: int) -> list[str]:
    candidates = sorted(
        glob.glob('data/result_*.csv') + glob.glob('data/**/*.csv', recursive=True),
        key=os.path.getmtime,
        reverse=True,
    )
    delta_files = []
    for path in candidates:
        base = os.path.basename(path)
        if base.startswith('result_') and path not in delta_files:
            delta_files.append(path)
        if len(delta_files) >= limit:
            break
    return delta_files


def main() -> None:
    parser = argparse.ArgumentParser(description='Process crawled delta CSV files through AI analysis and notification pipeline.')
    parser.add_argument('--csv', action='append', dest='csv_paths', help='Specific delta CSV path. Can be passed multiple times.')
    parser.add_argument('--latest', type=int, default=1, help='When --csv is not provided, process the latest N delta CSV files.')
    parser.add_argument('--config', default='config/pipeline_config.json', help='Pipeline config path.')
    parser.add_argument('--preferences', default='config/user_preferences.json', help='User preferences config path.')
    args = parser.parse_args()

    csv_paths = args.csv_paths or _find_latest_delta_files(args.latest)
    if not csv_paths:
        print('❌ No delta CSV files found.')
        return

    results = process_delta_files(csv_paths, config_path=args.config, preferences_path=args.preferences)
    for item in results:
        print(
            f"✅ Processed {item['csv_path']} imported={item['imported']} analyzed={item['analyzed']} notified={item['notified']}"
        )
        for name, path in item.get('digest_paths', {}).items():
            print(f'   - {name}: {path}')


if __name__ == '__main__':
    main()
