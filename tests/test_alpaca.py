import json

from ddt.connectors.alpaca.client import AlpacaClient
from ddt.cli import cmd_account


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, request, timeout=10):
        self.calls.append(
            {
                "url": request.full_url,
                "headers": {k.lower(): v for k, v in request.header_items()},
                "timeout": timeout,
            }
        )
        return FakeResponse(self.payload)


def test_get_account_uses_expected_endpoint_and_headers():
    transport = FakeTransport({"id": "acct-123", "status": "ACTIVE", "cash": "1000"})
    client = AlpacaClient(
        base_url="https://api.alpaca.markets",
        api_key="key123",
        api_secret="secret456",
        transport=transport,
    )

    account = client.get_account()

    assert account["id"] == "acct-123"
    assert transport.calls[0]["url"] == "https://api.alpaca.markets/v2/account"
    assert transport.calls[0]["headers"]["apca-api-key-id"] == "key123"
    assert transport.calls[0]["headers"]["apca-api-secret-key"] == "secret456"


def test_cmd_account_prints_account_json(capsys, monkeypatch):
    class StubClient:
        def get_account(self):
            return {"id": "acct-123", "status": "ACTIVE"}

    monkeypatch.setattr("ddt.cli._alpaca_client", lambda: StubClient())

    exit_code = cmd_account(None)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"id": "acct-123"' in captured.out
    assert '"status": "ACTIVE"' in captured.out
