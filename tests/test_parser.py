from research_spider.spider import parser_search


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
    assert record['pdf_url'] == 'https://arxiv.org/pdf/1234.5678'
