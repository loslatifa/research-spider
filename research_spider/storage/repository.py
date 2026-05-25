import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

import pandas as pd

from research_spider.storage.schema import SCHEMA_COLUMNS, ensure_dataframe_schema


class ResearchRepository:
    def __init__(self, db_path: str = 'data/research_spider.db') -> None:
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                '''
                CREATE TABLE IF NOT EXISTS papers (
                    uid TEXT PRIMARY KEY,
                    title TEXT,
                    authors TEXT,
                    venue TEXT,
                    year TEXT,
                    date TEXT,
                    doi TEXT,
                    abstract TEXT,
                    keywords TEXT,
                    abstract_url TEXT,
                    pdf_url TEXT,
                    url TEXT,
                    source TEXT,
                    query TEXT,
                    crawled_at TEXT,
                    record_hash TEXT,
                    change_type TEXT,
                    extra TEXT,
                    first_seen_at TEXT,
                    last_seen_at TEXT
                );

                CREATE TABLE IF NOT EXISTS analyses (
                    uid TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    model_name TEXT,
                    prompt_version TEXT,
                    analysis_json TEXT NOT NULL,
                    summary_zh TEXT,
                    topic_tags TEXT,
                    attention_score INTEGER,
                    should_follow INTEGER,
                    failure_reason TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (uid, record_hash)
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT NOT NULL,
                    record_hash TEXT,
                    channel TEXT NOT NULL,
                    priority_score REAL,
                    topic_key TEXT,
                    sent_at TEXT NOT NULL,
                    digest_path TEXT,
                    payload_json TEXT
                );
                '''
            )

    def upsert_papers(self, records: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
        rows = [dict(record) for record in records if record.get('uid')]
        if not rows:
            return []

        now_iso = datetime.now(timezone.utc).isoformat()
        events: List[Dict[str, str]] = []
        with self._connect() as conn:
            for record in rows:
                existing = conn.execute(
                    'SELECT uid, record_hash, first_seen_at FROM papers WHERE uid = ?',
                    (record['uid'],),
                ).fetchone()
                change_type = record.get('change_type') or 'new'
                if existing:
                    if existing['record_hash'] == record.get('record_hash'):
                        change_type = record.get('change_type') or 'unchanged'
                    else:
                        change_type = record.get('change_type') or 'updated'
                record['change_type'] = change_type
                first_seen_at = existing['first_seen_at'] if existing else now_iso

                columns = SCHEMA_COLUMNS + ['first_seen_at', 'last_seen_at']
                values = [record.get(column, '') for column in SCHEMA_COLUMNS] + [first_seen_at, now_iso]
                placeholders = ', '.join('?' for _ in columns)
                update_clause = ', '.join(f'{column} = excluded.{column}' for column in columns[1:])
                conn.execute(
                    f'''
                    INSERT INTO papers ({', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT(uid) DO UPDATE SET
                    {update_clause}
                    ''',
                    values,
                )
                events.append({
                    'uid': record['uid'],
                    'record_hash': record.get('record_hash', ''),
                    'change_type': change_type,
                })
        return events

    def get_records_needing_analysis(self, limit: int = 50, uids: Optional[Iterable[str]] = None) -> List[Dict[str, str]]:
        query = '''
            SELECT p.*
            FROM papers p
            LEFT JOIN analyses a
              ON a.uid = p.uid AND a.record_hash = p.record_hash
            WHERE a.uid IS NULL
              AND p.change_type IN ('new', 'updated')
        '''
        params: List = []
        if uids:
            uid_list = [uid for uid in uids if uid]
            if uid_list:
                placeholders = ', '.join('?' for _ in uid_list)
                query += f' AND p.uid IN ({placeholders})'
                params.extend(uid_list)
        query += '''
            ORDER BY COALESCE(p.date, p.crawled_at) DESC, p.crawled_at DESC
            LIMIT ?
        '''
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def save_analysis(
        self,
        uid: str,
        record_hash: str,
        analysis: Dict,
        model_name: str,
        prompt_version: str,
        failure_reason: str = '',
    ) -> None:
        payload = json.dumps(analysis, ensure_ascii=False)
        summary_zh = analysis.get('summary_zh', '')
        topic_tags = json.dumps(analysis.get('topic_tags', []), ensure_ascii=False)
        attention_score = int(analysis.get('attention_score', 0) or 0)
        should_follow = 1 if analysis.get('attention_recommendation', {}).get('should_follow') else 0
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO analyses (
                    uid, record_hash, model_name, prompt_version, analysis_json,
                    summary_zh, topic_tags, attention_score, should_follow,
                    failure_reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(uid, record_hash) DO UPDATE SET
                    model_name = excluded.model_name,
                    prompt_version = excluded.prompt_version,
                    analysis_json = excluded.analysis_json,
                    summary_zh = excluded.summary_zh,
                    topic_tags = excluded.topic_tags,
                    attention_score = excluded.attention_score,
                    should_follow = excluded.should_follow,
                    failure_reason = excluded.failure_reason,
                    created_at = excluded.created_at
                ''',
                (
                    uid,
                    record_hash,
                    model_name,
                    prompt_version,
                    payload,
                    summary_zh,
                    topic_tags,
                    attention_score,
                    should_follow,
                    failure_reason,
                    created_at,
                ),
            )

    def get_analysis_for_uids(self, uids: Iterable[str]) -> Dict[str, Dict]:
        uid_list = [uid for uid in uids if uid]
        if not uid_list:
            return {}
        placeholders = ', '.join('?' for _ in uid_list)
        query = f'''
            SELECT a.uid, a.analysis_json
            FROM analyses a
            JOIN papers p ON p.uid = a.uid AND p.record_hash = a.record_hash
            WHERE a.uid IN ({placeholders})
        '''
        with self._connect() as conn:
            rows = conn.execute(query, uid_list).fetchall()
        results = {}
        for row in rows:
            try:
                results[row['uid']] = json.loads(row['analysis_json'])
            except json.JSONDecodeError:
                continue
        return results

    def get_recent_notifications(self, hours: int = 24) -> List[Dict[str, str]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM notifications WHERE sent_at >= ? ORDER BY sent_at DESC',
                (cutoff.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_notifications(self, items: Iterable[Dict], channel: str, digest_path: str = '') -> None:
        rows = list(items)
        if not rows:
            return
        sent_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for item in rows:
                conn.execute(
                    '''
                    INSERT INTO notifications (
                        uid, record_hash, channel, priority_score, topic_key, sent_at, digest_path, payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        item.get('uid', ''),
                        item.get('record_hash', ''),
                        channel,
                        float(item.get('priority_score', 0.0) or 0.0),
                        item.get('topic_key', ''),
                        sent_at,
                        digest_path,
                        json.dumps(item, ensure_ascii=False),
                    ),
                )

    def import_csv(self, csv_path: str) -> List[Dict[str, str]]:
        if not os.path.exists(csv_path):
            return []
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        df = ensure_dataframe_schema(df)
        return self.upsert_papers(df.to_dict(orient='records'))
