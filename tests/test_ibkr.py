import json

import pytest

from ddt.cli import cmd_ibkr_accounts, cmd_ibkr_search_contracts, cmd_ibkr_status
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
