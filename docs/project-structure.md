# Project Structure

This repository is organized around the research intelligence pipeline:

```text
research-spider/
├── config/                # Crawl, pipeline, and user preference config
├── docs/                  # Project documentation and planning notes
├── research_spider/       # Application source package
│   ├── analyzer/          # AI and fallback paper analysis
│   ├── notifier/          # Console, Markdown, and JSON digest outputs
│   ├── pipeline/          # Orchestration from delta CSV to digest
│   ├── recommender/       # Scoring, cooldown, and topic limits
│   ├── spider/            # Fetching, parsing, robots checks, validation
│   └── storage/           # Shared schema and SQLite repository
├── resources/             # Static resources such as stop-word lists
├── scripts/               # CLI entry points and utility scripts
├── tests/                 # Unit and integration tests
├── README.md              # Project overview and usage
└── requirements.txt       # Python dependencies
```

## Source Code

Core reusable code lives under `research_spider/`:

- `research_spider/spider/` handles crawling concerns: fetch, parse, robots, validation, and crawl orchestration.
- `research_spider/storage/` owns the shared paper schema, record normalization, incremental detection, and SQLite persistence.
- `research_spider/analyzer/` owns AI analysis prompts, schemas, provider calls, and local fallback analysis.
- `research_spider/recommender/` owns priority scoring and notification suppression logic.
- `research_spider/notifier/` owns digest formatting and output channels.
- `research_spider/pipeline/` connects imported delta records to analysis, recommendation, and notification.
- `scripts/` contains executable entry points such as `run_spider`, `run_paper_pipeline`, `auto_runner`, `keyword_crawl_all`, and `analyze_data`.

Run scripts as modules from the repository root, for example `python -m scripts.run_spider --list`.

## Configuration

Configuration belongs in `config/`:

- `sites_to_crawl.csv` lists regular crawl sources.
- `sites_to_crawl_full.csv` supports keyword search templates.
- `pipeline_config.json` controls storage, analysis, recommendation, and notification behavior.
- `user_preferences.json` stores the current research-interest profile.

## Resources

Static runtime resources belong in `resources/`:

- `research_stop_words.txt` is used by `scripts/analyze_data.py` for n-gram filtering.

## Generated Artifacts

Generated data should stay out of version control:

- `data/*.csv` and local SQLite databases are crawl outputs; they are ignored and should not be committed.
- `data/notifications/` contains generated digests; generated Markdown and JSON digests are ignored.
- `figures/` contains generated charts and word clouds; files in this directory are ignored and should not be committed.
- `logs/` contains runtime logs.
- Python caches and test caches are ignored.

## Planning Artifacts

Planning and backlog artifacts live under `docs/planning/`:

- `docs/planning/codex-progress.txt`
- `docs/planning/feature_list.json`
