import json

import pandas as pd
import pytest

from research_spider.pipeline.config import load_pipeline_config
from research_spider.pipeline.orchestrator import process_delta_file
from research_spider.storage.repository import ResearchRepository
from research_spider.storage.schema import SCHEMA_COLUMNS, normalize_record


@pytest.fixture(autouse=True)
def isolate_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in [
        'AI_PROVIDER',
        'LLM_PROVIDER',
        'OPENAI_API_KEY',
        'QWEN_API_KEY',
        'DASHSCOPE_API_KEY',
    ]:
        monkeypatch.delenv(key, raising=False)


def test_load_pipeline_config_rejects_invalid_preferences(tmp_path):
    config_path = tmp_path / 'pipeline_config.json'
    preferences_path = tmp_path / 'user_preferences.json'
    config_path.write_text('{}', encoding='utf-8')
    preferences_path.write_text(json.dumps({
        'keywords': 'agent',
    }), encoding='utf-8')

    with pytest.raises(ValueError, match='preferences.keywords must be a list'):
        load_pipeline_config(config_path=str(config_path), preferences_path=str(preferences_path))


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
    assert result['run_id']
    assert result['analyzed'] == 1
    assert result['notified'] == 1
    assert 'json' in result['digest_paths']

    latest_run = ResearchRepository(str(db_path)).get_latest_run()
    assert latest_run['run_id'] == result['run_id']
    assert latest_run['status'] == 'completed'
    assert latest_run['imported'] == 1
    assert latest_run['analyzed'] == 1
    assert latest_run['notified'] == 1
    assert 'json' in latest_run['digest_paths']


def test_process_delta_file_accepts_qwen_analysis_config_without_api_key(tmp_path):
    csv_path = tmp_path / 'delta.csv'
    db_path = tmp_path / 'research.db'
    config_path = tmp_path / 'pipeline_config.json'
    preferences_path = tmp_path / 'user_preferences.json'

    record = normalize_record(
        {
            'title': 'A New Agent Benchmark',
            'authors': 'Alice, Bob',
            'abstract': 'We introduce a new benchmark for agent systems.',
            'keywords': 'agent, benchmark',
            'url': 'https://example.com/paper'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-14T00:00:00+00:00',
        query='agent',
    )
    record['change_type'] = 'new'
    pd.DataFrame([record], columns=SCHEMA_COLUMNS).to_csv(csv_path, index=False)

    config_path.write_text(json.dumps({
        'db_path': str(db_path),
        'analysis': {
            'provider': 'qwen',
            'model': 'qwen3.5-plus',
            'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        },
        'notification': {
            'enabled': False,
        },
        'recommendation': {
            'min_priority_score': 40,
            'max_batch_size': 5
        }
    }), encoding='utf-8')
    preferences_path.write_text(json.dumps({
        'keywords': ['agent', 'benchmark'],
        'topics': ['智能体']
    }), encoding='utf-8')

    result = process_delta_file(str(csv_path), config_path=str(config_path), preferences_path=str(preferences_path))

    assert result['imported'] == 1
    assert result['analyzed'] == 1


def test_process_delta_file_prefilters_low_relevance_analysis_candidates(tmp_path):
    csv_path = tmp_path / 'delta.csv'
    db_path = tmp_path / 'research.db'
    config_path = tmp_path / 'pipeline_config.json'
    preferences_path = tmp_path / 'user_preferences.json'

    relevant = normalize_record(
        {
            'title': 'Agent Benchmark for Tool Use',
            'authors': 'Alice',
            'abstract': 'We introduce a benchmark for agent systems.',
            'keywords': 'agent, benchmark',
            'url': 'https://example.com/agent'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-14T00:00:00+00:00',
        query='agent',
    )
    relevant['change_type'] = 'new'
    unrelated = normalize_record(
        {
            'title': 'A Study of Historical Trade Routes',
            'authors': 'Bob',
            'abstract': 'This paper studies trade route records.',
            'keywords': 'history',
            'url': 'https://example.com/history'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-14T00:00:00+00:00',
        query='history',
    )
    unrelated['change_type'] = 'new'
    pd.DataFrame([relevant, unrelated], columns=SCHEMA_COLUMNS).to_csv(csv_path, index=False)

    config_path.write_text(json.dumps({
        'db_path': str(db_path),
        'analysis': {
            'prefilter_enabled': True,
            'prefilter_min_score': 1,
            'batch_limit': 10,
        },
        'notification': {
            'enabled': False,
        },
        'recommendation': {
            'min_priority_score': 40,
            'max_batch_size': 5
        }
    }), encoding='utf-8')
    preferences_path.write_text(json.dumps({
        'keywords': ['agent', 'benchmark'],
        'topics': ['智能体']
    }), encoding='utf-8')

    result = process_delta_file(str(csv_path), config_path=str(config_path), preferences_path=str(preferences_path))

    assert result['imported'] == 2
    assert result['analyzed'] == 1
    assert result['skipped_analysis'] == 1


def test_process_delta_file_reuses_analysis_by_record_hash(tmp_path):
    csv_path = tmp_path / 'delta.csv'
    db_path = tmp_path / 'research.db'
    config_path = tmp_path / 'pipeline_config.json'
    preferences_path = tmp_path / 'user_preferences.json'

    first = normalize_record(
        {
            'title': 'Agent Benchmark for Tool Use',
            'authors': 'Alice',
            'abstract': 'We introduce a benchmark for agent systems.',
            'keywords': 'agent, benchmark',
            'url': 'https://example.com/agent'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-14T00:00:00+00:00',
        query='agent',
    )
    first['change_type'] = 'new'
    pd.DataFrame([first], columns=SCHEMA_COLUMNS).to_csv(csv_path, index=False)

    config_path.write_text(json.dumps({
        'db_path': str(db_path),
        'analysis': {
            'prefilter_enabled': True,
            'prefilter_min_score': 1,
            'batch_limit': 10,
        },
        'notification': {
            'enabled': False,
        },
        'recommendation': {
            'min_priority_score': 40,
            'max_batch_size': 5
        }
    }), encoding='utf-8')
    preferences_path.write_text(json.dumps({
        'keywords': ['agent', 'benchmark'],
        'topics': ['智能体']
    }), encoding='utf-8')

    first_result = process_delta_file(str(csv_path), config_path=str(config_path), preferences_path=str(preferences_path))
    assert first_result['analyzed'] == 1
    assert first_result['reused_analysis'] == 0

    second = first.copy()
    second['uid'] = 'sha1:manually-distinct-uid'
    second['change_type'] = 'new'
    pd.DataFrame([second], columns=SCHEMA_COLUMNS).to_csv(csv_path, index=False)

    second_result = process_delta_file(str(csv_path), config_path=str(config_path), preferences_path=str(preferences_path))

    assert second_result['imported'] == 1
    assert second_result['analyzed'] == 0
    assert second_result['reused_analysis'] == 1
