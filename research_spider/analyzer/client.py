import json
import os
from typing import Dict, List

import requests


class AIClientUnavailable(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(self) -> None:
        self.api_key = os.getenv('OPENAI_API_KEY', '').strip()
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini').strip()
        self.timeout = int(os.getenv('OPENAI_TIMEOUT_SECONDS', '60'))

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat_json(self, messages: List[Dict[str, str]]) -> Dict:
        if not self.available:
            raise AIClientUnavailable('OPENAI_API_KEY is not configured')

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
