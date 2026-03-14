ANALYSIS_SCHEMA_VERSION = 'v1'

ANALYSIS_JSON_SCHEMA = {
    'type': 'object',
    'required': [
        'title_zh',
        'summary_zh',
        'research_problem',
        'methodology',
        'innovations',
        'topic_tags',
        'attention_score',
        'attention_recommendation',
        'limitations_or_risks',
        'confidence',
    ],
    'properties': {
        'title_zh': {'type': 'string'},
        'summary_zh': {'type': 'string'},
        'research_problem': {'type': 'string'},
        'methodology': {'type': 'string'},
        'innovations': {'type': 'array', 'items': {'type': 'string'}},
        'topic_tags': {'type': 'array', 'items': {'type': 'string'}},
        'attention_score': {'type': 'integer', 'minimum': 0, 'maximum': 100},
        'attention_recommendation': {
            'type': 'object',
            'required': ['should_follow', 'reason'],
            'properties': {
                'should_follow': {'type': 'boolean'},
                'reason': {'type': 'string'},
            },
        },
        'limitations_or_risks': {'type': 'array', 'items': {'type': 'string'}},
        'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
    },
}
