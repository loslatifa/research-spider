import os
from typing import Dict, Iterable, List

import pandas as pd

from analyzer.pipeline import PaperAnalysisPipeline
from notifier.dispatcher import NotificationDispatcher
from pipeline.config import load_pipeline_config
from recommender.scoring import build_recommendations
from storage.repository import ResearchRepository
from storage.schema import ensure_dataframe_schema


def _load_records(csv_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(csv_path):
        return []
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df = ensure_dataframe_schema(df)
    return df.to_dict(orient='records')


def process_delta_file(csv_path: str, config_path: str = 'config/pipeline_config.json', preferences_path: str = 'config/user_preferences.json') -> Dict:
    config = load_pipeline_config(config_path=config_path, preferences_path=preferences_path)
    repository = ResearchRepository(config['db_path'])
    records = _load_records(csv_path)
    if not records:
        return {'csv_path': csv_path, 'imported': 0, 'analyzed': 0, 'notified': 0, 'digest_paths': {}}

    events = repository.upsert_papers(records)
    event_map = {event['uid']: event for event in events}
    analyzed = 0
    if config['analysis'].get('enabled', True):
        pipeline = PaperAnalysisPipeline(
            max_retries=int(config['analysis'].get('max_retries', 3)),
            retry_backoff_seconds=float(config['analysis'].get('retry_backoff_seconds', 2)),
        )
        pending_records = repository.get_records_needing_analysis(
            limit=int(config['analysis'].get('batch_limit', 50)),
            uids=event_map.keys(),
        )
        for record in pending_records:
            analysis, failure_reason = pipeline.analyze(record)
            repository.save_analysis(
                uid=record['uid'],
                record_hash=record['record_hash'],
                analysis=analysis,
                model_name=pipeline.model_name,
                prompt_version=pipeline.prompt_version,
                failure_reason=failure_reason,
            )
            analyzed += 1

    event_uids = [event['uid'] for event in events if event.get('change_type') in {'new', 'updated'}]
    event_records = []
    for record in records:
        uid = record.get('uid')
        if uid in event_uids:
            merged_record = record.copy()
            merged_record.update(event_map.get(uid, {}))
            event_records.append(merged_record)
    analyses = repository.get_analysis_for_uids(event_uids)
    recent_notifications = repository.get_recent_notifications(hours=int(config['recommendation'].get('cooldown_hours', 24)))
    recommendations = build_recommendations(
        records=event_records,
        analyses=analyses,
        preferences=config['preferences'],
        recent_notifications=recent_notifications,
        min_priority_score=int(config['recommendation'].get('min_priority_score', 60)),
        per_topic_limit=int(config['recommendation'].get('per_topic_limit', 2)),
    )
    recommendations = recommendations[: int(config['recommendation'].get('max_batch_size', 10))]

    digest_paths = {}
    if recommendations and config['notification'].get('enabled', True):
        dispatcher = NotificationDispatcher(output_dir=config['notification'].get('output_dir', 'data/notifications'))
        digest_paths = dispatcher.dispatch(recommendations, channels=config['notification'].get('channels', ['console']))
        repository.save_notifications(
            recommendations,
            channel=','.join(config['notification'].get('channels', ['console'])),
            digest_path=digest_paths.get('markdown') or digest_paths.get('json') or '',
        )

    return {
        'csv_path': csv_path,
        'imported': len(records),
        'analyzed': analyzed,
        'notified': len(recommendations),
        'digest_paths': digest_paths,
    }


def process_delta_files(csv_paths: Iterable[str], config_path: str = 'config/pipeline_config.json', preferences_path: str = 'config/user_preferences.json') -> List[Dict]:
    return [
        process_delta_file(csv_path, config_path=config_path, preferences_path=preferences_path)
        for csv_path in csv_paths
    ]
