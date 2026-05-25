import pandas as pd

from research_spider.storage.schema import SCHEMA_COLUMNS, normalize_record, prepare_incremental_outputs


def test_prepare_incremental_outputs_detects_new_and_updated(tmp_path):
    master_path = tmp_path / 'master.csv'
    record_v1 = normalize_record(
        {
            'title': 'Paper A',
            'authors': 'Alice',
            'abstract': 'old abstract',
            'doi': '10.1000/test',
            'url': 'https://example.com/a'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-14T00:00:00+00:00',
        query='ml',
    )
    pd.DataFrame([record_v1], columns=SCHEMA_COLUMNS).to_csv(master_path, index=False)

    record_v2 = normalize_record(
        {
            'title': 'Paper A',
            'authors': 'Alice',
            'abstract': 'new abstract',
            'doi': '10.1000/test',
            'url': 'https://example.com/a'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-15T00:00:00+00:00',
        query='ml',
    )
    record_new = normalize_record(
        {
            'title': 'Paper B',
            'authors': 'Bob',
            'abstract': 'another abstract',
            'url': 'https://example.com/b'
        },
        base_url='https://example.com',
        crawled_at_iso='2026-03-15T00:00:00+00:00',
        query='ml',
    )

    df_delta, df_master, stats = prepare_incremental_outputs(
        pd.DataFrame([record_v2, record_new], columns=SCHEMA_COLUMNS),
        str(master_path),
    )

    assert stats['updated'] == 1
    assert stats['new'] == 1
    assert sorted(df_delta['change_type'].tolist()) == ['new', 'updated']
    assert len(df_master) == 2
