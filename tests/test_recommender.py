from research_spider.recommender.scoring import build_recommendations, estimate_preference_match, score_record


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
        'weak_keywords': [],
        'topics': ['扩散模型'],
        'sources': ['arxiv.org'],
    }
    assert 'Matched keywords: diffusion, agent' in result['recommendation_reasons']
    assert 'Matched topics: 扩散模型' in result['recommendation_reasons']
    assert 'Preferred source: arxiv.org' in result['recommendation_reasons']
    assert 'Newly discovered paper' in result['recommendation_reasons']
    assert 'AI assessment: Strong benchmark relevance.' in result['recommendation_reasons']


def test_negative_preferences_exclude_recommendations_and_prefilter_matches():
    record = {
        'uid': 'paper-2',
        'title': 'Diffusion benchmark for finance policy',
        'abstract': 'A diffusion benchmark with finance policy examples.',
        'keywords': 'diffusion, policy',
        'source': 'arxiv.org',
        'date': '2100-01-01',
        'change_type': 'new',
        'extra': '{}',
    }
    analysis = {
        'topic_tags': ['扩散模型'],
        'summary_zh': '摘要',
        'attention_score': 80,
        'attention_recommendation': {
            'should_follow': True,
            'reason': 'High model relevance.',
        },
    }
    preferences = {
        'keywords': ['diffusion', 'benchmark'],
        'negative_keywords': ['finance', 'policy'],
    }

    match = estimate_preference_match(record, preferences)
    recommendations = build_recommendations(
        records=[record],
        analyses={'paper-2': analysis},
        preferences=preferences,
        recent_notifications=[],
        min_priority_score=40,
    )

    assert match['score'] == 0
    assert match['exclusion']['negative_keywords'] == ['finance', 'policy']
    assert recommendations == []


def test_daily_recommendation_limit_caps_ranked_results():
    records = []
    analyses = {}
    for index in range(3):
        uid = f'paper-{index}'
        records.append({
            'uid': uid,
            'title': f'Agent benchmark {index}',
            'abstract': 'Agent benchmark for tool use.',
            'keywords': 'agent, benchmark',
            'source': 'arxiv.org',
            'date': '2100-01-01',
            'change_type': 'new',
            'extra': '{}',
        })
        analyses[uid] = {
            'topic_tags': ['agents'],
            'summary_zh': '摘要',
            'attention_score': 70 + index,
            'attention_recommendation': {
                'should_follow': True,
                'reason': 'Relevant.',
            },
        }

    recommendations = build_recommendations(
        records=records,
        analyses=analyses,
        preferences={
            'keywords': ['agent'],
            'daily_recommendation_limit': 2,
        },
        recent_notifications=[],
        min_priority_score=40,
        per_topic_limit=10,
    )

    assert [item['uid'] for item in recommendations] == ['paper-2', 'paper-1']
