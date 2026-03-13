from ddt.models import NewsEvent
from ddt.strategies.news_reaction import HeadlineReactionStrategy


def test_normalize_polygon_news_adds_sentiment_and_event_tags():
    from ddt.news.normalize import normalize_polygon_news_item

    item = {
        'title': 'NVDA wins cloud partnership and shares surge after earnings beat',
        'description': 'A strong quarter and new cloud deal.',
        'article_url': 'https://example.com/nvda',
        'tickers': ['NVDA'],
        'keywords': ['earnings', 'cloud'],
        'insights': [{'ticker': 'NVDA', 'sentiment': 'positive'}],
    }

    event = normalize_polygon_news_item(item)

    assert event.source == 'polygon'
    assert event.tickers == ['NVDA']
    assert event.metadata['sentiment'] == 'positive'
    assert 'earnings' in event.metadata['event_tags']
    assert 'partnership' in event.metadata['event_tags']


def test_enriched_strategy_uses_metadata_sentiment_to_build_proposals():
    event = NewsEvent(
        source='polygon',
        headline='NVDA mentioned in positive analyst note',
        summary='synthetic',
        url='https://example.com',
        tickers=['NVDA'],
        asset_classes=['equity'],
        metadata={'sentiment': 'positive', 'event_tags': ['analyst-upgrade']},
    )

    proposals = HeadlineReactionStrategy().generate([event])

    assert len(proposals) == 1
    assert proposals[0].side == 'buy'
    assert proposals[0].metadata['event_tags'] == ['analyst-upgrade']


def test_build_proposals_from_stored_events_filters_by_symbol(tmp_path, monkeypatch, capsys):
    from ddt import store as store_module
    from ddt.cli import cmd_build_proposals_from_events

    event_store = store_module.JsonlStore(tmp_path / 'events.jsonl')
    proposal_store = store_module.JsonlStore(tmp_path / 'proposals.jsonl')
    event_store.append(NewsEvent(
        source='polygon',
        headline='NVDA wins partnership',
        summary='synthetic',
        url='https://example.com/nvda',
        tickers=['NVDA'],
        asset_classes=['equity'],
        metadata={'sentiment': 'positive', 'event_tags': ['partnership']},
    ).to_dict())
    event_store.append(NewsEvent(
        source='polygon',
        headline='TSLA faces probe',
        summary='synthetic',
        url='https://example.com/tsla',
        tickers=['TSLA'],
        asset_classes=['equity'],
        metadata={'sentiment': 'negative', 'event_tags': ['regulatory']},
    ).to_dict())

    monkeypatch.setattr('ddt.cli.event_store', lambda: event_store)
    monkeypatch.setattr('ddt.cli.proposal_store', lambda: proposal_store)
    args = type('Args', (), {'symbol': 'NVDA'})()

    exit_code = cmd_build_proposals_from_events(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'NVDA' in captured.out
    rows = proposal_store.read_all()
    assert len(rows) == 1
    assert rows[0]['symbol'] == 'NVDA'
    assert rows[0]['side'] == 'buy'
