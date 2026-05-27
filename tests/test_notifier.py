import json
from pathlib import Path

from research_spider.notifier.dispatcher import NotificationDispatcher


def test_digest_outputs_include_summary(tmp_path):
    dispatcher = NotificationDispatcher(output_dir=str(tmp_path))
    items = [
        {
            'uid': 'paper-1',
            'title': 'Agent benchmark',
            'source': 'arxiv.org',
            'change_type': 'new',
            'topic_key': 'agents',
            'summary_zh': '摘要',
            'priority_score': 88,
            'recommendation_reasons': ['Matched keywords: agent'],
            'score_components': {'attention_score': 60, 'preference': 20},
            'url': 'https://example.com/a',
        },
        {
            'uid': 'paper-2',
            'title': 'Diffusion update',
            'source': 'openalex.org',
            'change_type': 'updated',
            'topic_key': 'diffusion',
            'summary_zh': '摘要',
            'priority_score': 72,
            'recommendation_reasons': ['Paper metadata changed since the previous crawl'],
            'url': 'https://example.com/b',
        },
    ]

    paths = dispatcher.dispatch(items, channels=['markdown', 'json'])

    markdown = Path(paths['markdown']).read_text(encoding='utf-8')
    assert '## Daily Overview' in markdown
    assert '- Total recommendations: 2' in markdown
    assert '- Top priority score: 88' in markdown
    assert '- Sources: arxiv.org=1, openalex.org=1' in markdown
    assert '## [88] Agent benchmark' in markdown

    payload = json.loads(Path(paths['json']).read_text(encoding='utf-8'))
    assert payload['summary']['total_items'] == 2
    assert payload['summary']['top_priority_score'] == 88
    assert payload['summary']['source_counts'] == {'arxiv.org': 1, 'openalex.org': 1}
    assert payload['summary']['change_counts'] == {'new': 1, 'updated': 1}
    assert len(payload['items']) == 2
