from research_spider.analyzer.client import OpenAICompatibleClient, load_dotenv


def test_client_defaults_to_openai(monkeypatch):
    for key in [
        'AI_PROVIDER',
        'LLM_PROVIDER',
        'OPENAI_API_KEY',
        'OPENAI_BASE_URL',
        'OPENAI_MODEL',
        'QWEN_API_KEY',
        'DASHSCOPE_API_KEY',
    ]:
        monkeypatch.delenv(key, raising=False)

    client = OpenAICompatibleClient()

    assert client.provider == 'openai'
    assert client.base_url == 'https://api.openai.com/v1'
    assert client.model == 'gpt-4.1-mini'
    assert not client.available


def test_client_supports_qwen_provider_with_dashscope_fallback_key(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'qwen')
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'dashscope-key')
    monkeypatch.delenv('QWEN_API_KEY', raising=False)
    monkeypatch.delenv('QWEN_BASE_URL', raising=False)
    monkeypatch.delenv('QWEN_MODEL', raising=False)

    client = OpenAICompatibleClient()

    assert client.provider == 'qwen'
    assert client.api_key == 'dashscope-key'
    assert client.base_url == 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    assert client.model == 'qwen3.5-plus'
    assert client.available


def test_client_accepts_explicit_qwen_overrides(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'openai')

    client = OpenAICompatibleClient(
        provider='qwen',
        api_key='explicit-key',
        base_url='https://example.com/v1/',
        model='custom-qwen',
        timeout=12,
    )

    assert client.provider == 'qwen'
    assert client.api_key == 'explicit-key'
    assert client.base_url == 'https://example.com/v1'
    assert client.model == 'custom-qwen'
    assert client.timeout == 12


def test_client_loads_dotenv_without_overriding_existing_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('AI_PROVIDER', raising=False)
    monkeypatch.setenv('QWEN_API_KEY', 'env-key')
    (tmp_path / '.env').write_text(
        '\n'.join([
            'AI_PROVIDER=qwen',
            'QWEN_API_KEY=dotenv-key',
            'QWEN_MODEL=qwen3.5-plus',
            'AI_TIMEOUT_SECONDS=7',
        ]),
        encoding='utf-8',
    )

    load_dotenv()
    client = OpenAICompatibleClient()

    assert client.provider == 'qwen'
    assert client.api_key == 'env-key'
    assert client.model == 'qwen3.5-plus'
    assert client.timeout == 7
