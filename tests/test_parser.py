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
