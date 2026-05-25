import json
import re
import time
from typing import Dict, List, Tuple

from research_spider.analyzer.client import OpenAICompatibleClient
from research_spider.analyzer.prompts import build_messages
from research_spider.analyzer.schema import ANALYSIS_SCHEMA_VERSION


class PaperAnalysisPipeline:
    def __init__(self, max_retries: int = 3, retry_backoff_seconds: float = 2.0) -> None:
        self.client = OpenAICompatibleClient()
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.model_name = self.client.model if self.client.available else 'heuristic-fallback'
        self.prompt_version = ANALYSIS_SCHEMA_VERSION

    def analyze(self, record: Dict[str, str]) -> Tuple[Dict, str]:
        if self.client.available:
            messages = build_messages(record)
            for attempt in range(1, self.max_retries + 1):
                try:
                    result = self.client.chat_json(messages)
                    return self._normalize_output(record, result), ''
                except Exception as exc:
                    if attempt == self.max_retries:
                        break
                    time.sleep(self.retry_backoff_seconds * attempt)
            failure_reason = f'ai_analysis_failed_after_retries:{type(exc).__name__}'
        else:
            failure_reason = 'ai_client_unavailable'
        return self._fallback_analysis(record), failure_reason

    def _normalize_output(self, record: Dict[str, str], result: Dict) -> Dict:
        normalized = {
            'title_zh': self._string(result.get('title_zh')) or record.get('title', ''),
            'summary_zh': self._string(result.get('summary_zh')),
            'research_problem': self._string(result.get('research_problem')),
            'methodology': self._string(result.get('methodology')),
            'innovations': self._string_list(result.get('innovations')),
            'topic_tags': self._string_list(result.get('topic_tags')),
            'attention_score': self._clamp_int(result.get('attention_score'), 0, 100),
            'attention_recommendation': {
                'should_follow': bool(result.get('attention_recommendation', {}).get('should_follow')),
                'reason': self._string(result.get('attention_recommendation', {}).get('reason')),
            },
            'limitations_or_risks': self._string_list(result.get('limitations_or_risks')),
            'confidence': self._clamp_float(result.get('confidence'), 0.0, 1.0),
        }
        return normalized

    def _fallback_analysis(self, record: Dict[str, str]) -> Dict:
        title = record.get('title', '')
        abstract = record.get('abstract', '')
        corpus = ' '.join(part for part in [title, abstract, record.get('keywords', ''), record.get('query', '')] if part).lower()
        topic_tags = self._heuristic_tags(corpus)
        innovations = self._heuristic_innovations(title, abstract)
        year = self._extract_year(record.get('year') or record.get('date'))
        score = 45
        if year and year >= 2024:
            score += 15
        if any(word in corpus for word in ['benchmark', 'survey', 'diffusion', 'transformer', 'foundation model', 'llm']):
            score += 15
        if abstract:
            score += 10
        score = max(0, min(100, score))
        should_follow = score >= 65
        summary = abstract[:180] if abstract else f'论文题目为《{title}》，当前仅基于有限元数据生成摘要，建议补充摘要或全文后再做深入分析。'
        methodology = '信息不足，推测为基于题目与摘要中提及方法的研究。'
        if any(word in corpus for word in ['benchmark', 'dataset']):
            methodology = '论文可能围绕数据集构建、基准评测或实验对比展开。'
        elif any(word in corpus for word in ['framework', 'system', 'pipeline']):
            methodology = '论文可能提出一个系统化框架或工程流水线，并通过实验验证效果。'
        elif any(word in corpus for word in ['diffusion', 'transformer', 'reinforcement', 'graph']):
            methodology = '论文可能采用主流机器学习模型架构，并针对具体任务进行改进。'

        return {
            'title_zh': title,
            'summary_zh': summary,
            'research_problem': '信息不足，依据题目推测论文聚焦于提升特定任务上的效果、效率或泛化能力。',
            'methodology': methodology,
            'innovations': innovations,
            'topic_tags': topic_tags,
            'attention_score': score,
            'attention_recommendation': {
                'should_follow': should_follow,
                'reason': '基于题目、摘要完整度、关键词热度与新近性进行启发式判断。',
            },
            'limitations_or_risks': [
                '当前分析未读取全文，可能遗漏关键实验细节。',
                '若摘要缺失，结论主要基于标题推断。',
            ] if not abstract else [
                '当前分析仅基于元数据和摘要，未核验全文实验细节。',
            ],
            'confidence': 0.45 if abstract else 0.25,
        }

    @staticmethod
    def _string(value) -> str:
        if value is None:
            return ''
        return str(value).strip()

    @staticmethod
    def _string_list(value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in re.split(r'[,;，；]', value) if item.strip()]
        return [str(value).strip()]

    @staticmethod
    def _clamp_int(value, low: int, high: int) -> int:
        try:
            parsed = int(value)
        except Exception:
            parsed = low
        return max(low, min(high, parsed))

    @staticmethod
    def _clamp_float(value, low: float, high: float) -> float:
        try:
            parsed = float(value)
        except Exception:
            parsed = low
        return max(low, min(high, parsed))

    @staticmethod
    def _extract_year(value: str) -> int:
        match = re.search(r'(19\d{2}|20\d{2}|2100)', value or '')
        return int(match.group(1)) if match else 0

    @staticmethod
    def _heuristic_tags(corpus: str) -> List[str]:
        mapping = {
            '大语言模型': ['llm', 'large language model', 'gpt'],
            '扩散模型': ['diffusion'],
            '强化学习': ['reinforcement learning'],
            '计算机视觉': ['vision', 'image', 'video'],
            '图学习': ['graph'],
            '自然语言处理': ['language', 'nlp', 'text'],
            '医学智能': ['medical', 'clinical', 'biomedical'],
            '推荐系统': ['recommendation', 'ranking'],
        }
        tags = [tag for tag, keywords in mapping.items() if any(keyword in corpus for keyword in keywords)]
        return tags[:5] or ['机器学习', '科研追踪']

    @staticmethod
    def _heuristic_innovations(title: str, abstract: str) -> List[str]:
        text = f'{title} {abstract}'.lower()
        innovations = []
        if any(word in text for word in ['new', 'novel', 'efficient']):
            innovations.append('可能提出了新的模型、训练策略或效率优化方法。')
        if any(word in text for word in ['benchmark', 'dataset']):
            innovations.append('可能构建了新的评测基准、数据集或系统化对比实验。')
        if any(word in text for word in ['robust', 'generalization', 'transfer']):
            innovations.append('可能强调模型鲁棒性、泛化能力或迁移性能提升。')
        return innovations[:3] or ['当前仅能从题目和摘要推测创新点，建议补充全文验证。']
