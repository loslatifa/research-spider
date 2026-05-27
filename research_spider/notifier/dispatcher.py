import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Iterable, List


class NotificationDispatcher:
    def __init__(self, output_dir: str = 'data/notifications') -> None:
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def dispatch(self, candidates: Iterable[Dict], channels: List[str]) -> Dict[str, str]:
        items = list(candidates)
        if not items:
            return {}
        paths: Dict[str, str] = {}
        if 'console' in channels:
            self._dispatch_console(items)
        if 'markdown' in channels:
            paths['markdown'] = self._dispatch_markdown(items)
        if 'json' in channels:
            paths['json'] = self._dispatch_json(items)
        return paths

    def _dispatch_console(self, items: List[Dict]) -> None:
        print('\n📬 High-value paper digest')
        summary = self._build_summary(items)
        print(
            f"Summary: total={summary['total_items']} "
            f"top_score={summary['top_priority_score']} "
            f"sources={summary['source_counts']}"
        )
        for index, item in enumerate(items, start=1):
            print(f"{index}. [{item['priority_score']}] {item['title']}")
            print(f"   - source={item.get('source', '')} change={item.get('change_type', '')} topic={item.get('topic_key', '')}")
            for reason in item.get('recommendation_reasons', []):
                print(f"   - reason={reason}")
            if item.get('url'):
                print(f"   - url={item['url']}")

    def _dispatch_markdown(self, items: List[Dict]) -> str:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.output_dir, f'digest_{timestamp}.md')
        summary = self._build_summary(items)
        lines = ['# Research Spider Digest', '', '## Daily Overview']
        lines.append(f"- Total recommendations: {summary['total_items']}")
        lines.append(f"- Top priority score: {summary['top_priority_score']}")
        lines.append(f"- Sources: {self._format_counts(summary['source_counts'])}")
        lines.append(f"- Changes: {self._format_counts(summary['change_counts'])}")
        lines.append(f"- Topics: {self._format_counts(summary['topic_counts'])}")
        lines.append('')
        for item in items:
            lines.append(f"## [{item['priority_score']}] {item['title']}")
            lines.append(f"- Source: {item.get('source', '')}")
            lines.append(f"- Change: {item.get('change_type', '')}")
            lines.append(f"- Topic: {item.get('topic_key', '')}")
            lines.append(f"- Summary: {item.get('summary_zh', '')}")
            reasons = item.get('recommendation_reasons', [])
            if reasons:
                lines.append('- Reasons:')
                for reason in reasons:
                    lines.append(f"  - {reason}")
            elif item.get('attention_reason'):
                lines.append(f"- Reason: {item.get('attention_reason', '')}")
            components = item.get('score_components', {})
            if components:
                component_text = ', '.join(f'{key}={value}' for key, value in components.items())
                lines.append(f"- Score components: {component_text}")
            if item.get('url'):
                lines.append(f"- URL: {item['url']}")
            if item.get('pdf_url'):
                lines.append(f"- PDF: {item['pdf_url']}")
            lines.append('')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(lines))
        return path

    def _dispatch_json(self, items: List[Dict]) -> str:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.output_dir, f'digest_{timestamp}.json')
        payload = {
            'summary': self._build_summary(items),
            'items': items,
        }
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def _build_summary(items: List[Dict]) -> Dict:
        source_counts = Counter(item.get('source') or 'unknown' for item in items)
        change_counts = Counter(item.get('change_type') or 'unknown' for item in items)
        topic_counts = Counter(item.get('topic_key') or 'general' for item in items)
        scores = [int(item.get('priority_score', 0) or 0) for item in items]
        return {
            'total_items': len(items),
            'top_priority_score': max(scores) if scores else 0,
            'source_counts': dict(source_counts.most_common()),
            'change_counts': dict(change_counts.most_common()),
            'topic_counts': dict(topic_counts.most_common()),
        }

    @staticmethod
    def _format_counts(counts: Dict[str, int]) -> str:
        if not counts:
            return 'none'
        return ', '.join(f'{key}={value}' for key, value in counts.items())
