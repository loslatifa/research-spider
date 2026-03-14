import json
from datetime import datetime, timezone
from typing import Dict, Iterable, List


def _safe_json_loads(value: str) -> Dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _extract_topic_key(item: Dict) -> str:
    tags = item.get('topic_tags') or []
    if tags:
        return '|'.join(tags[:2])
    if item.get('query'):
        return item['query']
    return item.get('source', 'general')


def _freshness_score(record: Dict) -> int:
    for field in ['date', 'crawled_at']:
        value = record.get(field, '')
        if not value:
            continue
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt = datetime.strptime(value[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        now = datetime.now(timezone.utc)
        age_days = max(0, (now - dt.astimezone(timezone.utc)).days)
        if age_days <= 7:
            return 20
        if age_days <= 30:
            return 15
        if age_days <= 90:
            return 8
        return 3
    return 0


def _preference_score(record: Dict, analysis: Dict, preferences: Dict) -> int:
    text = ' '.join([
        record.get('title', ''),
        record.get('abstract', ''),
        record.get('keywords', ''),
        record.get('query', ''),
        ' '.join(analysis.get('topic_tags', [])),
    ]).lower()
    score = 0
    for keyword in preferences.get('keywords', []):
        if keyword.lower() in text:
            score += 8
    for topic in preferences.get('topics', []):
        if topic.lower() in text:
            score += 10
    for source in preferences.get('sources', []):
        if source.lower() == record.get('source', '').lower():
            score += 5
    return min(score, 25)


def score_record(record: Dict, analysis: Dict, preferences: Dict) -> Dict:
    extra = _safe_json_loads(record.get('extra', ''))
    attention_score = int(analysis.get('attention_score', 0) or 0)
    citation_count = int(extra.get('citation_count', 0) or 0)
    citation_bonus = min(10, citation_count // 20) if citation_count > 0 else 0
    update_bonus = 5 if record.get('change_type') == 'updated' else 0
    freshness = _freshness_score(record)
    preference = _preference_score(record, analysis, preferences)
    total = min(100, attention_score + citation_bonus + update_bonus + freshness + preference)

    return {
        'uid': record.get('uid', ''),
        'record_hash': record.get('record_hash', ''),
        'title': record.get('title', ''),
        'source': record.get('source', ''),
        'query': record.get('query', ''),
        'authors': record.get('authors', ''),
        'date': record.get('date', ''),
        'url': record.get('url') or record.get('abstract_url', ''),
        'pdf_url': record.get('pdf_url', ''),
        'change_type': record.get('change_type', ''),
        'topic_tags': analysis.get('topic_tags', []),
        'summary_zh': analysis.get('summary_zh', ''),
        'attention_reason': analysis.get('attention_recommendation', {}).get('reason', ''),
        'should_follow': bool(analysis.get('attention_recommendation', {}).get('should_follow')),
        'priority_score': total,
        'topic_key': _extract_topic_key({**record, **analysis}),
    }


def apply_push_cooldown(candidates: List[Dict], recent_notifications: Iterable[Dict], cooldown_hours: int, per_topic_limit: int) -> List[Dict]:
    recent_by_uid = {item.get('uid'): item for item in recent_notifications}
    topic_counts: Dict[str, int] = {}
    filtered: List[Dict] = []

    for candidate in sorted(candidates, key=lambda item: item['priority_score'], reverse=True):
        if candidate['uid'] in recent_by_uid:
            continue
        topic_key = candidate.get('topic_key', 'general')
        if topic_counts.get(topic_key, 0) >= per_topic_limit:
            continue
        topic_counts[topic_key] = topic_counts.get(topic_key, 0) + 1
        filtered.append(candidate)
    return filtered


def build_recommendations(
    records: Iterable[Dict],
    analyses: Dict[str, Dict],
    preferences: Dict,
    recent_notifications: Iterable[Dict],
    min_priority_score: int = 60,
    per_topic_limit: int = 2,
) -> List[Dict]:
    scored = []
    for record in records:
        analysis = analyses.get(record.get('uid', ''))
        if not analysis:
            continue
        candidate = score_record(record, analysis, preferences)
        if candidate['priority_score'] < min_priority_score:
            continue
        if not candidate['should_follow'] and candidate['priority_score'] < (min_priority_score + 10):
            continue
        scored.append(candidate)

    return apply_push_cooldown(scored, recent_notifications, preferences.get('cooldown_hours', 24), per_topic_limit)
