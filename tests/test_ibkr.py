import json

import pytest

from ddt.cli import cmd_ibkr_accounts, cmd_ibkr_search_contracts, cmd_ibkr_status, cmd_ibkr_summary, cmd_ibkr_positions, cmd_ibkr_orders, cmd_ibkr_market_snapshot, cmd_ibkr_contract_details, cmd_ibkr_review_future
from ddt.config import Settings, validate_ibkr_settings
from ddt.connectors.ibkr.client import IbkrClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class SequenceTransport:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, request, timeout=10, context=None):
        self.calls.append({
            'url': request.full_url,
            'method': request.get_method(),
            'headers': {k.lower(): v for k, v in request.header_items()},
            'context': context is not None,
        })
        return FakeResponse(self.payloads.pop(0))


def test_validate_ibkr_settings_requires_account_id():
    settings = Settings(ibkr_base_url='https://localhost:5000/v1/api', ibkr_account_id='')

    with pytest.raises(ValueError):
        validate_ibkr_settings(settings)


def test_ibkr_list_accounts_hits_portfolio_accounts_endpoint():
    transport = SequenceTransport([[{'id': 'DU1234567'}]])
    client = IbkrClient(base_url='https://localhost:5000/v1/api', account_id='DU1234567', transport=transport, verify_ssl=False)

    accounts = client.list_accounts()

    assert accounts[0]['id'] == 'DU1234567'
    assert transport.calls[0]['url'] == 'https://localhost:5000/v1/api/portfolio/accounts'
    assert transport.calls[0]['context'] is True


def test_ibkr_search_contracts_hits_secdef_search_endpoint():
    transport = SequenceTransport([[{'symbol': 'CL', 'description': 'Crude Oil Future'}]])
    client = IbkrClient(base_url='https://localhost:5000/v1/api', account_id='DU1234567', transport=transport, verify_ssl=False)

    results = client.search_contracts('CL')

    assert results[0]['symbol'] == 'CL'
    assert transport.calls[0]['url'] == 'https://localhost:5000/v1/api/iserver/secdef/search?symbol=CL'


def test_cmd_ibkr_status_prints_config_summary(capsys, monkeypatch):
    class StubClient:
        def config_summary(self):
            return {'base_url': 'https://localhost:5000/v1/api', 'account_id': 'DU1234567', 'verify_ssl': 'False'}

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())

    exit_code = cmd_ibkr_status(None)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'DU1234567' in captured.out


def test_cmd_ibkr_accounts_prints_accounts(capsys, monkeypatch):
    class StubClient:
        def list_accounts(self):
            return [{'id': 'DU1234567'}]

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())

    exit_code = cmd_ibkr_accounts(None)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'DU1234567' in captured.out


def test_cmd_ibkr_search_contracts_prints_results(capsys, monkeypatch):
    class StubClient:
        def search_contracts(self, symbol):
            assert symbol == 'CL'
            return [{'symbol': 'CL', 'description': 'Crude Oil Future'}]

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())
    args = type('Args', (), {'symbol': 'CL'})()

    exit_code = cmd_ibkr_search_contracts(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'Crude Oil Future' in captured.out


def test_ibkr_account_summary_hits_pa_summary_endpoint():
    transport = SequenceTransport([{'accounts': [{'accountId': 'DU1234567', 'currency': 'USD'}]}])
    client = IbkrClient(base_url='https://localhost:5000/v1/api', account_id='DU1234567', transport=transport, verify_ssl=False)

    summary = client.account_summary()

    assert summary['accounts'][0]['accountId'] == 'DU1234567'
    assert transport.calls[0]['url'] == 'https://localhost:5000/v1/api/portfolio/DU1234567/summary'


def test_ibkr_positions_hits_positions_endpoint():
    transport = SequenceTransport([[{'conid': 123, 'position': 2}]])
    client = IbkrClient(base_url='https://localhost:5000/v1/api', account_id='DU1234567', transport=transport, verify_ssl=False)

    positions = client.positions()

    assert positions[0]['conid'] == 123
    assert transport.calls[0]['url'] == 'https://localhost:5000/v1/api/portfolio/DU1234567/positions/0'


def test_ibkr_open_orders_hits_account_orders_endpoint():
    transport = SequenceTransport([{'orders': [{'orderId': '1', 'ticker': 'CL'}]}])
    client = IbkrClient(base_url='https://localhost:5000/v1/api', account_id='DU1234567', transport=transport, verify_ssl=False)

    orders = client.open_orders()

    assert orders['orders'][0]['ticker'] == 'CL'
    assert transport.calls[0]['url'] == 'https://localhost:5000/v1/api/iserver/account/orders'


def test_ibkr_market_snapshot_hits_marketdata_snapshot_endpoint():
    transport = SequenceTransport([[{'conid': 173418084, '31': '80.25', '_updated': 1234567890}]])
    client = IbkrClient(base_url='https://localhost:5000/v1/api', account_id='DU1234567', transport=transport, verify_ssl=False)

    snapshot = client.market_snapshot('173418084')

    assert snapshot[0]['conid'] == 173418084
    assert transport.calls[0]['url'] == 'https://localhost:5000/v1/api/iserver/marketdata/snapshot?conids=173418084&fields=31,84,85,86,88'


def test_ibkr_contract_details_hits_secdef_info_endpoint():
    transport = SequenceTransport([[{'conid': 173418084, 'symbol': 'CL', 'maturityDate': '202504'}]])
    client = IbkrClient(base_url='https://localhost:5000/v1/api', account_id='DU1234567', transport=transport, verify_ssl=False)

    details = client.contract_details('173418084')

    assert details[0]['symbol'] == 'CL'
    assert transport.calls[0]['url'] == 'https://localhost:5000/v1/api/iserver/secdef/info?conid=173418084'


def test_cmd_ibkr_summary_prints_account_summary(capsys, monkeypatch):
    class StubClient:
        def account_summary(self):
            return {'accounts': [{'accountId': 'DU1234567'}]}

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())
    exit_code = cmd_ibkr_summary(None)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'DU1234567' in captured.out


def test_cmd_ibkr_positions_prints_positions(capsys, monkeypatch):
    class StubClient:
        def positions(self):
            return [{'conid': 123, 'position': 2}]

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())
    exit_code = cmd_ibkr_positions(None)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '123' in captured.out


def test_cmd_ibkr_orders_prints_orders(capsys, monkeypatch):
    class StubClient:
        def open_orders(self):
            return {'orders': [{'orderId': '1', 'ticker': 'CL'}]}

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())
    exit_code = cmd_ibkr_orders(None)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'CL' in captured.out


def test_cmd_ibkr_market_snapshot_prints_snapshot(capsys, monkeypatch):
    class StubClient:
        def market_snapshot(self, conid):
            assert conid == '173418084'
            return [{'conid': 173418084, '31': '80.25'}]

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())
    args = type('Args', (), {'conid': '173418084'})()
    exit_code = cmd_ibkr_market_snapshot(args)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert '80.25' in captured.out


def test_cmd_ibkr_contract_details_prints_details(capsys, monkeypatch):
    class StubClient:
        def contract_details(self, conid):
            assert conid == '173418084'
            return [{'conid': 173418084, 'symbol': 'CL'}]

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())
    args = type('Args', (), {'conid': '173418084'})()
    exit_code = cmd_ibkr_contract_details(args)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'CL' in captured.out


def test_cmd_ibkr_review_future_prints_search_details_snapshot_and_account(capsys, monkeypatch):
    class StubClient:
        def search_contracts(self, symbol):
            assert symbol == 'CL'
            return [{'conid': 173418084, 'symbol': 'CL', 'description': 'Crude Oil Future'}]
        def contract_details(self, conid):
            assert conid == '173418084'
            return [{'conid': 173418084, 'symbol': 'CL', 'maturityDate': '202504'}]
        def market_snapshot(self, conid):
            assert conid == '173418084'
            return [{'conid': 173418084, '31': '80.25'}]
        def account_summary(self):
            return {'accounts': [{'accountId': 'DU1234567'}]}
        def positions(self):
            return []
        def open_orders(self):
            return {'orders': []}

    monkeypatch.setattr('ddt.cli._ibkr_client', lambda: StubClient())
    args = type('Args', (), {'symbol': 'CL', 'conid': '173418084'})()
    exit_code = cmd_ibkr_review_future(args)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'Crude Oil Future' in captured.out
    assert '80.25' in captured.out
    assert 'DU1234567' in captured.out
