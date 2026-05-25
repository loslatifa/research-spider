import json
import os
from copy import deepcopy
from typing import Dict


DEFAULT_CONFIG = {
    'db_path': 'data/research_spider.db',
    'analysis': {
        'enabled': True,
        'max_retries': 3,
        'retry_backoff_seconds': 2,
        'batch_limit': 50,
    },
    'recommendation': {
        'min_priority_score': 60,
        'per_topic_limit': 2,
        'cooldown_hours': 24,
        'max_batch_size': 10,
    },
    'notification': {
        'enabled': True,
        'channels': ['console', 'markdown', 'json'],
        'output_dir': 'data/notifications',
    },
    'preferences': {
        'topics': [],
        'keywords': [],
        'sources': [],
        'cooldown_hours': 24,
    },
}


def _deep_merge(base: Dict, override: Dict) -> Dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_pipeline_config(config_path: str = 'config/pipeline_config.json', preferences_path: str = 'config/user_preferences.json') -> Dict:
    config = deepcopy(DEFAULT_CONFIG)
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = _deep_merge(config, json.load(handle))
    if os.path.exists(preferences_path):
        with open(preferences_path, 'r', encoding='utf-8') as handle:
            config['preferences'] = _deep_merge(config['preferences'], json.load(handle))
    return config
