import json

from ddt.cli import cmd_ingest_polygon_news, cmd_market_quote, cmd_review_market
from ddt.connectors.polygon.client import PolygonClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class SequenceTransport:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, request, timeout=10):
        self.calls.append({
            'url': request.full_url,
            'method': request.get_method(),
            'headers': {k.lower(): v for k, v in request.header_items()},
        })
        return FakeResponse(self.payloads.pop(0))


def test_polygon_last_trade_hits_expected_endpoint():
    transport = SequenceTransport([{'results': {'p': 123.45, 'T': 'AAPL'}}])
    client = PolygonClient(api_key='poly123', transport=transport)

    quote = client.get_last_trade('AAPL')

    assert quote['results']['p'] == 123.45
    assert transport.calls[0]['url'] == 'https://api.polygon.io/v2/last/trade/AAPL?apiKey=poly123'


def test_polygon_news_hits_expected_endpoint():
    transport = SequenceTransport([{'results': [{'title': 'Headline', 'article_url': 'https://example.com', 'description': 'desc', 'tickers': ['AAPL']}]}])
    client = PolygonClient(api_key='poly123', transport=transport)

    news = client.get_news('AAPL', limit=5)

    assert news['results'][0]['title'] == 'Headline'
    assert 'ticker=AAPL' in transport.calls[0]['url']
    assert 'limit=5' in transport.calls[0]['url']




def test_polygon_last_trade_falls_back_to_prev_close_on_http_error():
    from urllib.error import HTTPError

    class FallbackTransport:
        def __init__(self):
            self.calls = []

        def __call__(self, request, timeout=10):
            self.calls.append(request.full_url)
            if len(self.calls) == 1:
                raise HTTPError(request.full_url, 403, 'Forbidden', hdrs=None, fp=None)
            return FakeResponse({'results': [{'c': 111.11}]})

    client = PolygonClient(api_key='poly123', transport=FallbackTransport())

    quote = client.get_last_trade('AAPL')

    assert quote['results']['p'] == 111.11
    assert quote['results']['T'] == 'AAPL'

def test_cmd_market_quote_prints_quote(capsys, monkeypatch):
    class StubClient:
        def get_last_trade(self, symbol):
            assert symbol == 'AAPL'
            return {'results': {'T': 'AAPL', 'p': 123.45}}

    monkeypatch.setattr('ddt.cli._polygon_client', lambda: StubClient())
    args = type('Args', (), {'symbol': 'AAPL'})()

    exit_code = cmd_market_quote(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '123.45' in captured.out


def test_cmd_ingest_polygon_news_persists_events(capsys, monkeypatch, tmp_path):
    from ddt import store as store_module

    class StubClient:
        def get_news(self, symbol=None, limit=10):
            return {
                'results': [
                    {'title': 'Headline', 'article_url': 'https://example.com', 'description': 'desc', 'tickers': ['AAPL']}
                ]
            }

    monkeypatch.setattr('ddt.cli._polygon_client', lambda: StubClient())
    monkeypatch.setattr('ddt.cli.event_store', lambda: store_module.JsonlStore(tmp_path / 'events.jsonl'))
    args = type('Args', (), {'symbol': 'AAPL', 'limit': 10})()

    exit_code = cmd_ingest_polygon_news(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'ingested 1 polygon news events' in captured.out
    rows = store_module.JsonlStore(tmp_path / 'events.jsonl').read_all()
    assert rows[0]['headline'] == 'Headline'
    assert rows[0]['tickers'] == ['AAPL']


def test_cmd_review_market_prints_summary(capsys, monkeypatch):
    class StubAlpaca:
        def get_account(self):
            return {'status': 'ACTIVE', 'cash': '450'}
        def get_positions(self):
            return []
        def get_open_orders(self):
            return []
    class StubPolygon:
        def get_news(self, symbol=None, limit=5):
            return {'results': [{'title': 'Headline', 'tickers': ['AAPL']}]}

    monkeypatch.setattr('ddt.cli._alpaca_client', lambda: StubAlpaca())
    monkeypatch.setattr('ddt.cli._polygon_client', lambda: StubPolygon())
    args = type('Args', (), {'symbol': 'AAPL', 'limit': 5})()

    exit_code = cmd_review_market(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'ACTIVE' in captured.out
    assert 'Headline' in captured.out
