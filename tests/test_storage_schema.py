import pandas as pd

from research_spider.storage.schema import (
    SCHEMA_COLUMNS,
    normalize_record,
    prepare_incremental_outputs,
    summarize_field_completeness,
)


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


def test_normalize_record_uses_source_ids_when_doi_is_missing():
    arxiv_record = normalize_record(
        {
            'title': 'A paper',
            'authors': 'Alice',
            'arxiv_id': '2401.12345v2',
            'url': 'https://arxiv.org/abs/2401.12345v2',
        },
        base_url='https://arxiv.org/search',
        crawled_at_iso='2026-03-15T00:00:00+00:00',
    )
    pubmed_record = normalize_record(
        {
            'title': 'A paper',
            'authors': 'Alice',
            'pmid': '12345678',
            'url': 'https://pubmed.ncbi.nlm.nih.gov/12345678/',
        },
        base_url='https://pubmed.ncbi.nlm.nih.gov',
        crawled_at_iso='2026-03-15T00:00:00+00:00',
    )
    openalex_record = normalize_record(
        {
            'title': 'A paper',
            'authors': 'Alice',
            'openalex_id': 'https://openalex.org/W123',
            'url': 'https://openalex.org/W123',
        },
        base_url='https://api.openalex.org/works',
        crawled_at_iso='2026-03-15T00:00:00+00:00',
    )

    assert arxiv_record['uid'] == 'arxiv:2401.12345v2'
    assert pubmed_record['uid'] == 'pmid:12345678'
    assert openalex_record['uid'] == 'openalex:w123'


def test_normalize_record_prefers_doi_over_source_id_for_cross_source_dedupe():
    record = normalize_record(
        {
            'title': 'A paper',
            'authors': 'Alice',
            'doi': 'https://doi.org/10.1000/test',
            'openalex_id': 'https://openalex.org/W123',
        },
        base_url='https://api.openalex.org/works',
        crawled_at_iso='2026-03-15T00:00:00+00:00',
    )

    assert record['uid'] == 'doi:10.1000/test'


def test_summarize_field_completeness_counts_non_empty_values():
    df = pd.DataFrame(
        [
            {'title': 'A', 'url': 'https://example.com/a', 'abstract': 'summary'},
            {'title': 'B', 'url': '', 'abstract': ''},
        ]
    )

    summary = summarize_field_completeness(df, fields=['title', 'url', 'abstract', 'doi'])

    assert summary['title'] == {'present': 2, 'total': 2, 'rate': 1.0}
    assert summary['url'] == {'present': 1, 'total': 2, 'rate': 0.5}
    assert summary['abstract'] == {'present': 1, 'total': 2, 'rate': 0.5}
    assert summary['doi'] == {'present': 0, 'total': 2, 'rate': 0.0}
