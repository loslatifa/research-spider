import hashlib
import json
import os
import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple
from urllib.parse import urlparse

import pandas as pd

SCHEMA_COLUMNS = [
    'uid',
    'title',
    'authors',
    'venue',
    'year',
    'date',
    'doi',
    'abstract',
    'keywords',
    'abstract_url',
    'pdf_url',
    'url',
    'source',
    'query',
    'crawled_at',
    'record_hash',
    'change_type',
    'extra',
]

DEFAULT_COMPLETENESS_FIELDS = ['title', 'authors', 'url', 'abstract', 'doi']

_HASH_FIELDS = [
    'uid',
    'title',
    'authors',
    'venue',
    'year',
    'date',
    'doi',
    'abstract',
    'keywords',
    'abstract_url',
    'pdf_url',
    'url',
    'source',
    'query',
    'extra',
]


def _norm_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and pd.isna(value):
        return ''
    return str(value).strip()


def _norm_year(value: Any) -> str:
    text = _norm_text(value)
    if not text:
        return ''
    match = re.search(r'(19\d{2}|20\d{2}|2100)', text)
    return match.group(1) if match else text


def _norm_doi(value: Any) -> str:
    text = _norm_text(value).lower()
    if not text:
        return ''
    text = re.sub(r'^doi:\s*', '', text)
    text = re.sub(r'^https?://(dx\.)?doi\.org/', '', text)
    return text.strip()


def _normalize_keywords(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if isinstance(item, (list, tuple)):
                item = ', '.join(_norm_text(x) for x in item if _norm_text(x))
            parts.append(f'{key}:{_norm_text(item)}')
        return '; '.join(part for part in parts if part.strip(':'))
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        normalized = [_norm_text(item) for item in value if _norm_text(item)]
        return ', '.join(normalized)
    return _norm_text(value)


def reconstruct_openalex_abstract(inverted_index: Dict[str, List[int]]) -> str:
    if not inverted_index:
        return ''
    positions: Dict[int, str] = {}
    for token, indexes in inverted_index.items():
        for index in indexes:
            positions[index] = token
    return ' '.join(token for _, token in sorted(positions.items()))


def _norm_source_uid(record: Dict[str, Any]) -> str:
    source_id = _norm_text(record.get('source_id'))
    if source_id:
        return source_id.lower()

    arxiv_id = _norm_text(record.get('arxiv_id'))
    if arxiv_id:
        return f'arxiv:{arxiv_id.lower()}'

    pmid = _norm_text(record.get('pmid') or record.get('pubmed_id'))
    if pmid:
        pmid = re.sub(r'\D+', '', pmid)
        if pmid:
            return f'pmid:{pmid}'

    openalex_id = _norm_text(record.get('openalex_id'))
    if openalex_id:
        openalex_key = re.sub(r'^https?://openalex\.org/', '', openalex_id, flags=re.IGNORECASE)
        return f'openalex:{openalex_key.lower()}'

    return ''


def _make_uid(doi: Any, title: Any, authors: Any, year: Any, source_uid: Any = '') -> str:
    normalized_doi = _norm_doi(doi)
    if normalized_doi:
        return f'doi:{normalized_doi}'
    normalized_source_uid = _norm_text(source_uid).lower()
    if normalized_source_uid:
        return normalized_source_uid
    key = '|'.join([
        _norm_text(title).lower(),
        _norm_text(authors).lower(),
        _norm_year(year),
    ])
    return 'sha1:' + hashlib.sha1(key.encode('utf-8')).hexdigest()


def _build_record_hash(record: Dict[str, Any]) -> str:
    key = '|'.join(_norm_text(record.get(field, '')) for field in _HASH_FIELDS)
    return hashlib.sha1(key.encode('utf-8')).hexdigest()


def ensure_dataframe_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=SCHEMA_COLUMNS)
    normalized = df.copy()
    for column in SCHEMA_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ''
    normalized = normalized.fillna('')
    ordered = SCHEMA_COLUMNS + [col for col in normalized.columns if col not in SCHEMA_COLUMNS]
    return normalized[ordered]


def summarize_field_completeness(
    df: pd.DataFrame,
    fields: Sequence[str] = DEFAULT_COMPLETENESS_FIELDS,
) -> Dict[str, Dict[str, float]]:
    df = ensure_dataframe_schema(df)
    total = len(df)
    summary: Dict[str, Dict[str, float]] = {}
    for field in fields:
        if field not in df.columns:
            present = 0
        else:
            present = int(df[field].astype(str).str.strip().ne('').sum())
        summary[field] = {
            'present': present,
            'total': total,
            'rate': round((present / total), 4) if total else 0.0,
        }
    return summary


def load_master_dataframe(master_csv_path: str) -> pd.DataFrame:
    if not os.path.exists(master_csv_path):
        return pd.DataFrame(columns=SCHEMA_COLUMNS)
    try:
        df = pd.read_csv(master_csv_path, dtype=str, keep_default_na=False)
    except Exception:
        return pd.DataFrame(columns=SCHEMA_COLUMNS)
    return ensure_dataframe_schema(df)


def normalize_record(record: Dict[str, Any], base_url: str, crawled_at_iso: str, query: str = '') -> Dict[str, str]:
    source = urlparse(base_url).netloc or _norm_text(base_url)

    title = record.get('title') or record.get('paper_title') or record.get('quote_text') or ''
    authors = record.get('authors') or record.get('author') or ''
    venue = (
        record.get('journal')
        or record.get('journal_info')
        or record.get('venue')
        or record.get('conference')
        or record.get('primary_location')
        or ''
    )
    year = record.get('year') or record.get('pub_year') or record.get('publication_year') or ''
    date = record.get('date') or record.get('pub_date') or record.get('publication_date') or record.get('submitted_date') or ''
    doi = record.get('doi') or record.get('DOI') or record.get('doi_url') or ''
    abstract = (
        record.get('abstract')
        or record.get('summary')
        or record.get('description')
        or record.get('abstract_text')
        or ''
    )
    keywords = record.get('keywords') or record.get('tags') or record.get('concepts') or ''
    abstract_url = record.get('abstract_url') or record.get('abstract_link') or record.get('url') or ''
    pdf_url = record.get('pdf_url') or record.get('fulltext_url') or record.get('pdf') or ''
    url = record.get('url') or record.get('source_url') or abstract_url or ''

    source_uid = _norm_source_uid(record)
    uid = _make_uid(doi, title, authors, year or date, source_uid=source_uid)

    excluded_fields = {
        'title', 'paper_title', 'quote_text',
        'authors', 'author',
        'journal', 'journal_info', 'venue', 'conference', 'primary_location',
        'year', 'pub_year', 'publication_year',
        'date', 'pub_date', 'publication_date', 'submitted_date',
        'doi', 'DOI', 'doi_url',
        'abstract', 'summary', 'description', 'abstract_text',
        'keywords', 'tags', 'concepts',
        'abstract_url', 'abstract_link', 'pdf_url', 'fulltext_url', 'pdf',
        'url', 'source_url',
    }
    extra = {key: value for key, value in record.items() if key not in excluded_fields}

    normalized = {
        'uid': uid,
        'title': _norm_text(title),
        'authors': _norm_text(authors),
        'venue': _norm_text(venue),
        'year': _norm_year(year or date),
        'date': _norm_text(date),
        'doi': _norm_doi(doi),
        'abstract': _norm_text(abstract),
        'keywords': _normalize_keywords(keywords),
        'abstract_url': _norm_text(abstract_url),
        'pdf_url': _norm_text(pdf_url),
        'url': _norm_text(url),
        'source': _norm_text(source),
        'query': _norm_text(query),
        'crawled_at': _norm_text(crawled_at_iso),
        'record_hash': '',
        'change_type': '',
        'extra': json.dumps(extra, ensure_ascii=False) if extra else '',
    }
    normalized['record_hash'] = _build_record_hash(normalized)
    return {column: normalized.get(column, '') for column in SCHEMA_COLUMNS}


def prepare_incremental_outputs(df_new: pd.DataFrame, master_csv_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    df_new = ensure_dataframe_schema(df_new).drop_duplicates(subset=['uid'], keep='last')
    if not df_new.empty:
        df_new['record_hash'] = df_new.apply(lambda row: row['record_hash'] or _build_record_hash(row.to_dict()), axis=1)

    df_master = load_master_dataframe(master_csv_path)
    master_hash_by_uid = dict(zip(df_master['uid'], df_master['record_hash'])) if not df_master.empty else {}

    delta_rows = []
    stats = {'new': 0, 'updated': 0, 'unchanged': 0}
    for _, row in df_new.iterrows():
        row_dict = row.to_dict()
        uid = row_dict.get('uid', '')
        if not uid:
            continue
        existing_hash = master_hash_by_uid.get(uid)
        if not existing_hash:
            row_dict['change_type'] = 'new'
            stats['new'] += 1
            delta_rows.append(row_dict)
        elif existing_hash != row_dict.get('record_hash'):
            row_dict['change_type'] = 'updated'
            stats['updated'] += 1
            delta_rows.append(row_dict)
        else:
            stats['unchanged'] += 1

    df_delta = ensure_dataframe_schema(pd.DataFrame(delta_rows, columns=SCHEMA_COLUMNS))
    if df_delta.empty:
        return df_delta, df_master, stats

    remaining_master = df_master[~df_master['uid'].isin(df_delta['uid'])].copy() if not df_master.empty else df_master
    df_master_updated = pd.concat([remaining_master, df_delta], ignore_index=True)
    df_master_updated = ensure_dataframe_schema(df_master_updated).drop_duplicates(subset=['uid'], keep='last')
    return df_delta, df_master_updated, stats
