from research_spider.spider import parser, parser_search


def test_parse_arxiv_search_page_extracts_structured_fields():
    html = '''
    <ol>
      <li class="arxiv-result">
        <p class="title is-5 mathjax">Example Paper</p>
        <p class="authors">Authors: Alice, Bob</p>
        <p class="list-title is-inline-block"><a href="https://arxiv.org/abs/1234.5678">abs</a></p>
        <a href="/pdf/1234.5678">pdf</a>
        <span class="abstract-full has-text-grey-dark mathjax">This is an abstract. △ Less</span>
        <span class="tag">machine learning</span>
        <span class="tag">diffusion</span>
        <p class="is-size-7">Submitted 1 March, 2026</p>
      </li>
    </ol>
    '''

    records = parser_search.parse_arxiv_search_page(html, url='https://arxiv.org/search/?query=test')

    assert len(records) == 1
    record = records[0]
    assert record['title'] == 'Example Paper'
    assert record['authors'] == 'Alice, Bob'
    assert record['abstract'] == 'This is an abstract.'
    assert record['keywords'] == 'machine learning, diffusion'
    assert record['arxiv_id'] == '1234.5678'
    assert record['pdf_url'] == 'https://arxiv.org/pdf/1234.5678'


def test_parse_pubmed_search_page_extracts_pmid():
    html = '''
    <article class="full-docsum">
      <a class="docsum-title" href="/12345678/">A clinical AI paper</a>
      <span class="docsum-authors full-authors">Alice, Bob</span>
      <span class="docsum-journal-citation full-journal-citation">J Test. 2026.</span>
    </article>
    '''

    records = parser_search.parse_pubmed_search_page(html, url='https://pubmed.ncbi.nlm.nih.gov/?term=ai')

    assert len(records) == 1
    record = records[0]
    assert record['title'] == 'A clinical AI paper'
    assert record['pmid'] == '12345678'
    assert record['abstract_url'] == 'https://pubmed.ncbi.nlm.nih.gov/12345678/'


def test_parse_openalex_json_extracts_openalex_id():
    payload = {
        'results': [
            {
                'id': 'https://openalex.org/W123',
                'title': 'OpenAlex paper',
                'authorships': [{'author': {'display_name': 'Alice'}}],
                'primary_location': {'source': {'display_name': 'Venue'}},
            }
        ]
    }

    records = parser.parse_openalex_json(payload, url='https://api.openalex.org/works')

    assert len(records) == 1
    assert records[0]['openalex_id'] == 'https://openalex.org/W123'
    assert records[0]['url'] == 'https://openalex.org/W123'


def test_parse_crossref_json_extracts_structured_fields():
    payload = {
        'message': {
            'items': [
                {
                    'title': ['Crossref Paper'],
                    'author': [{'given': 'Alice', 'family': 'Smith'}],
                    'container-title': ['Journal of Tests'],
                    'published-online': {'date-parts': [[2026, 3, 1]]},
                    'DOI': '10.1000/crossref',
                    'URL': 'https://doi.org/10.1000/crossref',
                    'is-referenced-by-count': 7,
                }
            ]
        }
    }

    records = parser.parse_crossref_json(payload, url='https://api.crossref.org/works')

    assert len(records) == 1
    assert records[0]['title'] == 'Crossref Paper'
    assert records[0]['authors'] == 'Alice Smith'
    assert records[0]['venue'] == 'Journal of Tests'
    assert records[0]['doi'] == '10.1000/crossref'
    assert records[0]['publication_year'] == '2026'


def test_parse_europe_pmc_json_extracts_identifiers():
    payload = {
        'resultList': {
            'result': [
                {
                    'id': 'MED123',
                    'pmid': '12345',
                    'title': 'Europe PMC Paper',
                    'authorString': 'Alice et al.',
                    'journalTitle': 'Medical Tests',
                    'pubYear': '2026',
                    'abstractText': 'Clinical abstract.',
                }
            ]
        }
    }

    records = parser.parse_europe_pmc_json(payload, url='https://www.ebi.ac.uk/europepmc/webservices/rest/search')

    assert len(records) == 1
    assert records[0]['title'] == 'Europe PMC Paper'
    assert records[0]['pmid'] == '12345'
    assert records[0]['source_id'] == 'pmid:12345'


def test_parse_semantic_scholar_json_extracts_external_ids():
    payload = {
        'data': [
            {
                'paperId': 'abc123',
                'title': 'Semantic Scholar Paper',
                'authors': [{'name': 'Alice'}, {'name': 'Bob'}],
                'year': 2026,
                'abstract': 'A useful abstract.',
                'url': 'https://www.semanticscholar.org/paper/abc123',
                'externalIds': {'DOI': '10.1000/semantic', 'ArXiv': '2401.1'},
                'openAccessPdf': {'url': 'https://example.com/paper.pdf'},
            }
        ]
    }

    records = parser.parse_semantic_scholar_json(payload, url='https://api.semanticscholar.org/graph/v1/paper/search')

    assert len(records) == 1
    assert records[0]['semantic_scholar_id'] == 'abc123'
    assert records[0]['authors'] == 'Alice, Bob'
    assert records[0]['doi'] == '10.1000/semantic'
    assert records[0]['arxiv_id'] == '2401.1'
