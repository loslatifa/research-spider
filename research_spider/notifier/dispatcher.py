import json
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple


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
        for index, item in enumerate(items, start=1):
            print(f"{index}. [{item['priority_score']}] {item['title']}")
            print(f"   - source={item.get('source', '')} change={item.get('change_type', '')} topic={item.get('topic_key', '')}")
            print(f"   - reason={item.get('attention_reason', '')}")
            if item.get('url'):
                print(f"   - url={item['url']}")

    def _dispatch_markdown(self, items: List[Dict]) -> str:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.output_dir, f'digest_{timestamp}.md')
        lines = ['# Research Spider Digest', '']
        for item in items:
            lines.append(f"## [{item['priority_score']}] {item['title']}")
            lines.append(f"- Source: {item.get('source', '')}")
            lines.append(f"- Change: {item.get('change_type', '')}")
            lines.append(f"- Topic: {item.get('topic_key', '')}")
            lines.append(f"- Summary: {item.get('summary_zh', '')}")
            lines.append(f"- Reason: {item.get('attention_reason', '')}")
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
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(items, handle, ensure_ascii=False, indent=2)
        return path
