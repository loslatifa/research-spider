import json
from typing import Dict, List

from analyzer.schema import ANALYSIS_JSON_SCHEMA, ANALYSIS_SCHEMA_VERSION


SYSTEM_PROMPT = (
    '你是资深科研论文分析助手。你必须基于输入论文元数据输出稳定 JSON，'
    '不要输出 Markdown，不要输出额外解释，不要臆造未给出的事实。'
    '若信息不足，字段保留简洁并明确标注信息不足。所有文字说明使用中文。'
)


def build_messages(record: Dict[str, str]) -> List[Dict[str, str]]:
    payload = {
        'uid': record.get('uid', ''),
        'title': record.get('title', ''),
        'authors': record.get('authors', ''),
        'venue': record.get('venue', ''),
        'year': record.get('year', ''),
        'date': record.get('date', ''),
        'doi': record.get('doi', ''),
        'abstract': record.get('abstract', ''),
        'keywords': record.get('keywords', ''),
        'source': record.get('source', ''),
        'query': record.get('query', ''),
        'extra': record.get('extra', ''),
    }
    user_prompt = (
        f'请分析下面的论文信息，并严格输出符合 schema_version={ANALYSIS_SCHEMA_VERSION} 的 JSON。\n'
        '规则:\n'
        '1. `title_zh` 为中文标题翻译或中文转述。\n'
        '2. `summary_zh` 尽量控制在 120-180 字。\n'
        '3. `research_problem` 提炼论文想解决的核心问题。\n'
        '4. `methodology` 提炼主要方法。\n'
        '5. `innovations` 输出 1-3 条。\n'
        '6. `topic_tags` 输出 2-5 个中文主题标签。\n'
        '7. `attention_score` 为 0-100 的整数。\n'
        '8. `attention_recommendation.should_follow` 判断是否值得持续关注。\n'
        '9. `limitations_or_risks` 输出 0-3 条潜在局限。\n'
        '10. `confidence` 为 0-1 浮点数。\n'
        '11. 不允许输出 schema 以外字段。\n\n'
        f'JSON Schema:\n{json.dumps(ANALYSIS_JSON_SCHEMA, ensure_ascii=False)}\n\n'
        f'论文元数据:\n{json.dumps(payload, ensure_ascii=False)}'
    )
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': user_prompt},
    ]
