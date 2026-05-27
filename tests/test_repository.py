from research_spider.storage.repository import ResearchRepository


def test_repository_records_run_history(tmp_path):
    repository = ResearchRepository(str(tmp_path / 'research.db'))

    run_id = repository.start_run('data/result_arxiv.csv')
    repository.finish_run(
        run_id,
        status='completed',
        imported=3,
        analyzed=2,
        reused_analysis=1,
        skipped_analysis=0,
        notified=2,
        digest_paths={'markdown': 'data/notifications/digest.md'},
    )

    latest = repository.get_latest_run()

    assert latest['run_id'] == run_id
    assert latest['csv_path'] == 'data/result_arxiv.csv'
    assert latest['status'] == 'completed'
    assert latest['imported'] == 3
    assert latest['analyzed'] == 2
    assert latest['reused_analysis'] == 1
    assert latest['notified'] == 2
    assert latest['digest_paths'] == {'markdown': 'data/notifications/digest.md'}
