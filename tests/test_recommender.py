from research_spider.recommender.scoring import score_record


def test_score_record_includes_explainable_recommendation_fields():
    record = {
        'uid': 'paper-1',
        'record_hash': 'hash-1',
        'title': 'Diffusion benchmark for agents',
        'abstract': 'A benchmark for diffusion agents.',
        'keywords': 'diffusion, benchmark',
        'source': 'arxiv.org',
        'date': '2100-01-01',
        'change_type': 'new',
        'extra': '{"citation_count": 45}',
    }
    analysis = {
        'topic_tags': ['扩散模型'],
        'summary_zh': '摘要',
        'attention_score': 50,
        'attention_recommendation': {
            'should_follow': True,
            'reason': 'Strong benchmark relevance.',
        },
    }
    preferences = {
        'keywords': ['diffusion', 'agent'],
        'topics': ['扩散模型'],
        'sources': ['arxiv.org'],
    }

    result = score_record(record, analysis, preferences)

    assert result['priority_score'] == 97
    assert result['score_components'] == {
        'attention_score': 50,
        'citation_bonus': 2,
        'update_bonus': 0,
        'freshness': 20,
        'preference': 25,
    }
    assert result['matched_preferences'] == {
        'keywords': ['diffusion', 'agent'],
        'topics': ['扩散模型'],
        'sources': ['arxiv.org'],
    }
    assert 'Matched keywords: diffusion, agent' in result['recommendation_reasons']
    assert 'Matched topics: 扩散模型' in result['recommendation_reasons']
    assert 'Preferred source: arxiv.org' in result['recommendation_reasons']
    assert 'Newly discovered paper' in result['recommendation_reasons']
    assert 'AI assessment: Strong benchmark relevance.' in result['recommendation_reasons']
