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


def test_build_proposals_from_stored_events_only_emits_requested_symbol(tmp_path, monkeypatch, capsys):
    from ddt import store as store_module
    from ddt.cli import cmd_build_proposals_from_events

    event_store = store_module.JsonlStore(tmp_path / 'events.jsonl')
    proposal_store = store_module.JsonlStore(tmp_path / 'proposals.jsonl')
    event_store.append(NewsEvent(
        source='polygon',
        headline='NVDA and VCIG announce AI partnership',
        summary='synthetic',
        url='https://example.com/multi',
        tickers=['NVDA', 'VCIG'],
        asset_classes=['equity'],
        metadata={'sentiment': 'positive', 'event_tags': ['partnership']},
    ).to_dict())

    monkeypatch.setattr('ddt.cli.event_store', lambda: event_store)
    monkeypatch.setattr('ddt.cli.proposal_store', lambda: proposal_store)
    args = type('Args', (), {'symbol': 'NVDA', 'limit': 5})()

    exit_code = cmd_build_proposals_from_events(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"symbol": "NVDA"' in captured.out
    assert '"symbol": "VCIG"' not in captured.out
    rows = proposal_store.read_all()
    assert len(rows) == 1
    assert rows[0]['symbol'] == 'NVDA'


def test_cmd_review_symbol_prints_quote_news_events_and_proposals(tmp_path, monkeypatch, capsys):
    from ddt import store as store_module
    from ddt.cli import cmd_review_symbol

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

    class StubAlpaca:
        def get_account(self):
            return {'status': 'ACTIVE', 'cash': '450'}
        def get_positions(self):
            return []
        def get_open_orders(self):
            return []
        def get_clock(self):
            return {'is_open': True}
        def preview_order(self, symbol, side, qty, time_in_force, asset_class='equity'):
            return {'symbol': symbol, 'side': side, 'qty': qty, 'asset_class': asset_class, 'status': 'preview_only'}

    class StubPolygon:
        def get_last_trade(self, symbol):
            return {'results': {'T': symbol, 'p': 100.0}}
        def get_news(self, symbol=None, limit=5):
            return {'results': [{'title': 'NVDA wins partnership', 'tickers': ['NVDA']}]}

    monkeypatch.setattr('ddt.cli._alpaca_client', lambda: StubAlpaca())
    monkeypatch.setattr('ddt.cli._polygon_client', lambda: StubPolygon())
    monkeypatch.setattr('ddt.cli.event_store', lambda: event_store)
    monkeypatch.setattr('ddt.cli.proposal_store', lambda: proposal_store)
    args = type('Args', (), {'symbol': 'NVDA', 'limit': 5, 'side': 'buy', 'qty': '1', 'time_in_force': 'day', 'asset_class': 'equity'})()

    exit_code = cmd_review_symbol(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'NVDA wins partnership' in captured.out
    assert 'preview_only' in captured.out
    assert '100.0' in captured.out


def test_normalize_polygon_news_assigns_source_score_from_publisher():
    from ddt.news.normalize import normalize_polygon_news_item

    item = {
        'title': 'Company reports earnings beat',
        'description': 'desc',
        'article_url': 'https://example.com',
        'tickers': ['AAPL'],
        'publisher': {'name': 'The Motley Fool'},
    }

    event = normalize_polygon_news_item(item)

    assert event.metadata['source_name'] == 'The Motley Fool'
    assert event.metadata['source_score'] > 0.5


def test_enriched_strategy_adjusts_confidence_from_source_score_and_event_tags():
    event = NewsEvent(
        source='polygon',
        headline='NVDA wins partnership',
        summary='synthetic',
        url='https://example.com',
        tickers=['NVDA'],
        asset_classes=['equity'],
        metadata={
            'sentiment': 'positive',
            'event_tags': ['earnings', 'partnership'],
            'source_score': 0.9,
        },
    )

    proposals = HeadlineReactionStrategy().generate([event])

    assert len(proposals) == 1
    assert proposals[0].confidence > 0.7


def test_build_proposals_from_events_deduplicates_near_identical_proposals(tmp_path, monkeypatch, capsys):
    from ddt import store as store_module
    from ddt.cli import cmd_build_proposals_from_events

    event_store = store_module.JsonlStore(tmp_path / 'events.jsonl')
    proposal_store = store_module.JsonlStore(tmp_path / 'proposals.jsonl')
    common = {
        'source': 'polygon',
        'summary': 'synthetic',
        'url': 'https://example.com/nvda',
        'tickers': ['NVDA'],
        'asset_classes': ['equity'],
        'metadata': {'sentiment': 'positive', 'event_tags': ['partnership'], 'source_score': 0.8},
    }
    event_store.append(NewsEvent(headline='NVDA wins partnership with cloud giant', **common).to_dict())
    event_store.append(NewsEvent(headline='NVDA wins partnership with cloud giant', **common).to_dict())

    monkeypatch.setattr('ddt.cli.event_store', lambda: event_store)
    monkeypatch.setattr('ddt.cli.proposal_store', lambda: proposal_store)
    args = type('Args', (), {'symbol': 'NVDA', 'limit': 5})()

    exit_code = cmd_build_proposals_from_events(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    rows = proposal_store.read_all()
    assert len(rows) == 1


def test_cmd_backfill_event_metadata_updates_legacy_events(tmp_path, monkeypatch, capsys):
    from ddt import store as store_module
    from ddt.cli import cmd_backfill_event_metadata

    event_store = store_module.JsonlStore(tmp_path / 'events.jsonl')
    legacy = NewsEvent(
        source='polygon',
        headline='AAPL earnings beat and partnership announced',
        summary='legacy row',
        url='https://example.com/aapl',
        tickers=['AAPL'],
        asset_classes=['equity'],
        metadata={'publisher': {'name': 'The Motley Fool'}},
    )
    event_store.append(legacy.to_dict())

    monkeypatch.setattr('ddt.cli.event_store', lambda: event_store)
    args = type('Args', (), {})()

    exit_code = cmd_backfill_event_metadata(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'updated 1 events' in captured.out
    rows = event_store.read_all()
    assert rows[0]['metadata']['source_name'] == 'The Motley Fool'
    assert rows[0]['metadata']['source_score'] > 0.5
    assert 'earnings' in rows[0]['metadata']['event_tags']


def test_review_symbol_ranks_proposals_by_confidence_and_exposes_top_proposal(tmp_path, monkeypatch, capsys):
    from ddt import store as store_module
    from ddt.cli import cmd_review_symbol

    event_store = store_module.JsonlStore(tmp_path / 'events.jsonl')
    event_store.append(NewsEvent(
        source='polygon',
        headline='NVDA earnings beat and partnership expands',
        summary='high quality',
        url='https://example.com/nvda1',
        tickers=['NVDA'],
        asset_classes=['equity'],
        metadata={'sentiment': 'positive', 'event_tags': ['earnings', 'partnership'], 'source_score': 0.9, 'source_name': 'Bloomberg', 'dedupe_key': 'nvda earnings beat partnership'},
    ).to_dict())
    event_store.append(NewsEvent(
        source='polygon',
        headline='NVDA mentioned in market roundup',
        summary='weaker signal',
        url='https://example.com/nvda2',
        tickers=['NVDA'],
        asset_classes=['equity'],
        metadata={'sentiment': 'positive', 'event_tags': [], 'source_score': 0.5, 'source_name': 'unknown', 'dedupe_key': 'nvda market roundup'},
    ).to_dict())

    class StubAlpaca:
        def get_account(self): return {'status': 'ACTIVE'}
        def get_positions(self): return []
        def get_open_orders(self): return []
        def get_clock(self): return {'is_open': True}
        def preview_order(self, symbol, side, qty, time_in_force, asset_class='equity'):
            return {'symbol': symbol, 'side': side, 'qty': qty, 'asset_class': asset_class, 'status': 'preview_only'}

    class StubPolygon:
        def get_last_trade(self, symbol): return {'results': {'T': symbol, 'p': 100.0}}
        def get_news(self, symbol=None, limit=5): return {'results': []}

    monkeypatch.setattr('ddt.cli._alpaca_client', lambda: StubAlpaca())
    monkeypatch.setattr('ddt.cli._polygon_client', lambda: StubPolygon())
    monkeypatch.setattr('ddt.cli.event_store', lambda: event_store)
    args = type('Args', (), {'symbol': 'NVDA', 'limit': 5, 'side': 'buy', 'qty': '1', 'time_in_force': 'day', 'asset_class': 'equity'})()

    exit_code = cmd_review_symbol(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'ranked_proposals' in captured.out
    assert 'top_proposal' in captured.out
    import json
    payload = json.loads(captured.out)
    assert payload['top_proposal']['confidence'] >= payload['ranked_proposals'][1]['confidence']
    assert payload['top_proposal']['metadata']['source_name'] == 'Bloomberg'
