import json

import pandas as pd

from pipeline.orchestrator import process_delta_file
from storage.schema import SCHEMA_COLUMNS, normalize_record


def test_process_delta_file_runs_with_fallback_analysis(tmp_path):
    csv_path = tmp_path / 'delta.csv'
    db_path = tmp_path / 'research.db'
    config_path = tmp_path / 'pipeline_config.json'
    preferences_path = tmp_path / 'user_preferences.json'
    output_dir = tmp_path / 'notifications'

    record = normalize_record(
        {
            'title': 'A New Diffusion Benchmark',
            'authors': 'Alice, Bob',
            'abstract': 'We introduce a new benchmark for diffusion models.',
            'keywords': 'diffusion, benchmark',
            'url': 'https://example.com/paper'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-14T00:00:00+00:00',
        query='diffusion',
    )
    record['change_type'] = 'new'
    pd.DataFrame([record], columns=SCHEMA_COLUMNS).to_csv(csv_path, index=False)

    config_path.write_text(json.dumps({
        'db_path': str(db_path),
        'notification': {
            'enabled': True,
            'channels': ['json'],
            'output_dir': str(output_dir)
        },
        'recommendation': {
            'min_priority_score': 40,
            'max_batch_size': 5
        }
    }), encoding='utf-8')
    preferences_path.write_text(json.dumps({
        'keywords': ['diffusion', 'benchmark'],
        'topics': ['扩散模型']
    }), encoding='utf-8')

    result = process_delta_file(str(csv_path), config_path=str(config_path), preferences_path=str(preferences_path))

    assert result['imported'] == 1
    assert result['analyzed'] == 1
    assert result['notified'] == 1
    assert 'json' in result['digest_paths']
