import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import requests


class AIClientUnavailable(RuntimeError):
    pass


def load_dotenv(path: str = '.env') -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class OpenAICompatibleClient:
    PROVIDER_DEFAULTS = {
        'openai': {
            'api_key_env': 'OPENAI_API_KEY',
            'base_url_env': 'OPENAI_BASE_URL',
            'model_env': 'OPENAI_MODEL',
            'timeout_env': 'OPENAI_TIMEOUT_SECONDS',
            'base_url': 'https://api.openai.com/v1',
            'model': 'gpt-4.1-mini',
        },
        'qwen': {
            'api_key_env': 'QWEN_API_KEY',
            'fallback_api_key_env': 'DASHSCOPE_API_KEY',
            'base_url_env': 'QWEN_BASE_URL',
            'model_env': 'QWEN_MODEL',
            'timeout_env': 'QWEN_TIMEOUT_SECONDS',
            'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'model': 'qwen3.5-plus',
        },
    }

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        load_dotenv()
        self.provider = (provider or os.getenv('AI_PROVIDER') or os.getenv('LLM_PROVIDER') or 'openai').strip().lower()
        defaults = self.PROVIDER_DEFAULTS.get(self.provider, self.PROVIDER_DEFAULTS['openai'])

        api_key_env = defaults['api_key_env']
        fallback_api_key_env = defaults.get('fallback_api_key_env', '')
        env_api_key = os.getenv(api_key_env, '').strip() or (os.getenv(fallback_api_key_env, '').strip() if fallback_api_key_env else '')

        self.api_key = (api_key if api_key is not None else env_api_key).strip()
        self.base_url = (base_url or os.getenv(defaults['base_url_env'], '') or defaults['base_url']).rstrip('/')
        self.model = (model or os.getenv(defaults['model_env'], '') or defaults['model']).strip()
        timeout_value = (
            os.getenv('AI_TIMEOUT_SECONDS')
            or os.getenv(defaults.get('timeout_env', ''), '')
            or os.getenv('OPENAI_TIMEOUT_SECONDS')
            or '60'
        )
        self.timeout = int(timeout_value)
        if timeout is not None:
            self.timeout = int(timeout)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat_json(self, messages: List[Dict[str, str]]) -> Dict:
        if not self.available:
            raise AIClientUnavailable(f'{self.provider} API key is not configured')

        endpoint = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': 0.2,
            'response_format': {'type': 'json_object'},
        }
        response = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        if isinstance(content, list):
            content = ''.join(part.get('text', '') for part in content if isinstance(part, dict))
        return json.loads(content)
