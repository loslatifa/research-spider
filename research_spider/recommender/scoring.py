import json
from datetime import datetime, timezone
from typing import Dict, Iterable, List


def normalize_preferences(preferences: Dict) -> Dict:
    profile = preferences or {}
    positive_keywords = list(profile.get('keywords', []))
    positive_keywords.extend(profile.get('strong_keywords', []))
    weak_keywords = list(profile.get('weak_keywords', []))
    preferred_sources = list(profile.get('sources', []))
    preferred_sources.extend(profile.get('preferred_sources', []))

    return {
        **profile,
        'topics': list(profile.get('topics', [])),
        'keywords': positive_keywords,
        'weak_keywords': weak_keywords,
        'negative_keywords': list(profile.get('negative_keywords', [])),
        'excluded_topics': list(profile.get('excluded_topics', [])),
        'sources': preferred_sources,
        'excluded_sources': list(profile.get('excluded_sources', [])),
        'daily_recommendation_limit': profile.get('daily_recommendation_limit'),
    }


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


def _preference_signals(record: Dict, analysis: Dict, preferences: Dict) -> Dict:
    preferences = normalize_preferences(preferences)
    text = ' '.join([
        record.get('title', ''),
        record.get('abstract', ''),
        record.get('keywords', ''),
        record.get('query', ''),
        ' '.join(analysis.get('topic_tags', [])),
    ]).lower()
    score = 0
    matched_keywords = []
    matched_weak_keywords = []
    matched_topics = []
    matched_sources = []
    for keyword in preferences.get('keywords', []):
        if keyword.lower() in text:
            score += 8
            matched_keywords.append(keyword)
    for keyword in preferences.get('weak_keywords', []):
        if keyword.lower() in text:
            score += 3
            matched_weak_keywords.append(keyword)
    for topic in preferences.get('topics', []):
        if topic.lower() in text:
            score += 10
            matched_topics.append(topic)
    for source in preferences.get('sources', []):
        if source.lower() == record.get('source', '').lower():
            score += 5
            matched_sources.append(source)
    return {
        'score': min(score, 25),
        'matched_keywords': matched_keywords,
        'matched_weak_keywords': matched_weak_keywords,
        'matched_topics': matched_topics,
        'matched_sources': matched_sources,
    }


def estimate_preference_match(record: Dict, preferences: Dict) -> Dict:
    preferences = normalize_preferences(preferences)
    text = ' '.join([
        record.get('title', ''),
        record.get('abstract', ''),
        record.get('keywords', ''),
        record.get('query', ''),
    ]).lower()
    source_text = ' '.join([
        record.get('source', ''),
        record.get('url', ''),
        record.get('abstract_url', ''),
        record.get('pdf_url', ''),
    ]).lower()
    matched_keywords = [
        keyword for keyword in preferences.get('keywords', [])
        if keyword and keyword.lower() in text
    ]
    matched_weak_keywords = [
        keyword for keyword in preferences.get('weak_keywords', [])
        if keyword and keyword.lower() in text
    ]
    matched_topics = [
        topic for topic in preferences.get('topics', [])
        if topic and topic.lower() in text
    ]
    matched_sources = [
        source for source in preferences.get('sources', [])
        if source and source.lower() in source_text
    ]
    blocked = exclusion_signals(record, {}, preferences)
    if blocked['is_excluded']:
        score = 0
    else:
        score = (
            len(matched_keywords) * 2
            + len(matched_weak_keywords)
            + len(matched_topics) * 3
            + len(matched_sources)
        )
    return {
        'score': score,
        'matched_keywords': matched_keywords,
        'matched_weak_keywords': matched_weak_keywords,
        'matched_topics': matched_topics,
        'matched_sources': matched_sources,
        'exclusion': blocked,
    }


def exclusion_signals(record: Dict, analysis: Dict, preferences: Dict) -> Dict:
    preferences = normalize_preferences(preferences)
    text = ' '.join([
        record.get('title', ''),
        record.get('abstract', ''),
        record.get('keywords', ''),
        record.get('query', ''),
        ' '.join(analysis.get('topic_tags', [])),
    ]).lower()
    source_text = ' '.join([
        record.get('source', ''),
        record.get('url', ''),
        record.get('abstract_url', ''),
        record.get('pdf_url', ''),
    ]).lower()
    matched_negative_keywords = [
        keyword for keyword in preferences.get('negative_keywords', [])
        if keyword and keyword.lower() in text
    ]
    matched_excluded_topics = [
        topic for topic in preferences.get('excluded_topics', [])
        if topic and topic.lower() in text
    ]
    matched_excluded_sources = [
        source for source in preferences.get('excluded_sources', [])
        if source and source.lower() in source_text
    ]
    return {
        'is_excluded': bool(
            matched_negative_keywords
            or matched_excluded_topics
            or matched_excluded_sources
        ),
        'negative_keywords': matched_negative_keywords,
        'excluded_topics': matched_excluded_topics,
        'excluded_sources': matched_excluded_sources,
    }


def _build_recommendation_reasons(
    record: Dict,
    analysis: Dict,
    preference_signals: Dict,
    components: Dict[str, int],
) -> List[str]:
    reasons = []
    if preference_signals['matched_keywords']:
        reasons.append('Matched keywords: ' + ', '.join(preference_signals['matched_keywords']))
    if preference_signals.get('matched_weak_keywords'):
        reasons.append('Matched weak keywords: ' + ', '.join(preference_signals['matched_weak_keywords']))
    if preference_signals['matched_topics']:
        reasons.append('Matched topics: ' + ', '.join(preference_signals['matched_topics']))
    if preference_signals['matched_sources']:
        reasons.append('Preferred source: ' + ', '.join(preference_signals['matched_sources']))
    if record.get('change_type') == 'updated':
        reasons.append('Paper metadata changed since the previous crawl')
    elif record.get('change_type') == 'new':
        reasons.append('Newly discovered paper')
    if components.get('freshness', 0) >= 15:
        reasons.append('Recent publication or crawl date')
    if components.get('citation_bonus', 0) > 0:
        reasons.append(f"Citation signal contributed +{components['citation_bonus']} points")
    attention_reason = analysis.get('attention_recommendation', {}).get('reason', '')
    if attention_reason:
        reasons.append('AI assessment: ' + attention_reason)
    return reasons


def score_record(record: Dict, analysis: Dict, preferences: Dict) -> Dict:
    preferences = normalize_preferences(preferences)
    extra = _safe_json_loads(record.get('extra', ''))
    attention_score = int(analysis.get('attention_score', 0) or 0)
    citation_count = int(extra.get('citation_count', 0) or 0)
    citation_bonus = min(10, citation_count // 20) if citation_count > 0 else 0
    update_bonus = 5 if record.get('change_type') == 'updated' else 0
    freshness = _freshness_score(record)
    preference_signals = _preference_signals(record, analysis, preferences)
    preference = preference_signals['score']
    components = {
        'attention_score': attention_score,
        'citation_bonus': citation_bonus,
        'update_bonus': update_bonus,
        'freshness': freshness,
        'preference': preference,
    }
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
        'score_components': components,
        'matched_preferences': {
            'keywords': preference_signals['matched_keywords'],
            'weak_keywords': preference_signals['matched_weak_keywords'],
            'topics': preference_signals['matched_topics'],
            'sources': preference_signals['matched_sources'],
        },
        'recommendation_reasons': _build_recommendation_reasons(
            record,
            analysis,
            preference_signals,
            components,
        ),
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
    preferences = normalize_preferences(preferences)
    scored = []
    for record in records:
        analysis = analyses.get(record.get('uid', ''))
        if not analysis:
            continue
        if exclusion_signals(record, analysis, preferences)['is_excluded']:
            continue
        candidate = score_record(record, analysis, preferences)
        if candidate['priority_score'] < min_priority_score:
            continue
        if not candidate['should_follow'] and candidate['priority_score'] < (min_priority_score + 10):
            continue
        scored.append(candidate)

    filtered = apply_push_cooldown(scored, recent_notifications, preferences.get('cooldown_hours', 24), per_topic_limit)
    daily_limit = preferences.get('daily_recommendation_limit')
    if daily_limit is None:
        return filtered
    return filtered[: int(daily_limit)]
