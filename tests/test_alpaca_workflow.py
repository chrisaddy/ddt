import json

import pytest

from ddt.cli import cmd_preview_order, cmd_submit_order
from ddt.config import Settings, validate_alpaca_settings
from ddt.connectors.alpaca.client import AlpacaClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class SequenceTransport:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, request, timeout=10):
        body = request.data.decode("utf-8") if request.data else None
        self.calls.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "headers": {k.lower(): v for k, v in request.header_items()},
                "body": body,
                "timeout": timeout,
            }
        )
        payload = self.payloads.pop(0)
        return FakeResponse(payload)


def test_get_positions_hits_positions_endpoint():
    transport = SequenceTransport([[{"symbol": "AAPL", "qty": "2"}]])
    client = AlpacaClient(
        base_url="https://api.alpaca.markets",
        api_key="key123",
        api_secret="secret456",
        transport=transport,
    )

    positions = client.get_positions()

    assert positions[0]["symbol"] == "AAPL"
    assert transport.calls[0]["url"] == "https://api.alpaca.markets/v2/positions"
    assert transport.calls[0]["method"] == "GET"


def test_get_open_orders_hits_orders_endpoint_with_open_status():
    transport = SequenceTransport([[{"id": "ord-1", "status": "new"}]])
    client = AlpacaClient(
        base_url="https://api.alpaca.markets",
        api_key="key123",
        api_secret="secret456",
        transport=transport,
    )

    orders = client.get_open_orders()

    assert orders[0]["id"] == "ord-1"
    assert transport.calls[0]["url"] == "https://api.alpaca.markets/v2/orders?status=open&direction=desc"


def test_submit_order_posts_expected_payload():
    transport = SequenceTransport([{"id": "ord-1", "status": "accepted"}])
    client = AlpacaClient(
        base_url="https://api.alpaca.markets",
        api_key="key123",
        api_secret="secret456",
        transport=transport,
    )

    order = client.submit_order(symbol="AAPL", side="buy", qty="1", time_in_force="day")

    assert order["id"] == "ord-1"
    assert transport.calls[0]["method"] == "POST"
    assert transport.calls[0]["url"] == "https://api.alpaca.markets/v2/orders"
    assert json.loads(transport.calls[0]["body"]) == {
        "symbol": "AAPL",
        "side": "buy",
        "type": "market",
        "qty": "1",
        "time_in_force": "day",
    }


def test_validate_alpaca_settings_raises_when_missing_keys():
    settings = Settings(alpaca_api_key="", alpaca_api_secret="", alpaca_base_url="https://api.alpaca.markets")

    with pytest.raises(ValueError):
        validate_alpaca_settings(settings)


def test_cmd_preview_order_prints_preview(capsys):
    args = type(
        "Args",
        (),
        {"symbol": "AAPL", "side": "buy", "qty": "1", "time_in_force": "day", "asset_class": "equity"},
    )()

    exit_code = cmd_preview_order(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"symbol": "AAPL"' in captured.out
    assert '"status": "preview_only"' in captured.out


def test_cmd_submit_order_requires_confirm_flag(capsys):
    args = type(
        "Args",
        (),
        {"symbol": "AAPL", "side": "buy", "qty": "1", "time_in_force": "day", "confirm": False},
    )()

    exit_code = cmd_submit_order(args)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert '--confirm' in captured.out


def test_cmd_submit_order_calls_client_when_confirmed(capsys, monkeypatch):
    class StubClient:
        def submit_order(self, symbol, side, qty, time_in_force):
            assert symbol == "AAPL"
            assert side == "buy"
            assert qty == "1"
            assert time_in_force == "day"
            return {"id": "ord-1", "status": "accepted"}

    monkeypatch.setattr("ddt.cli._alpaca_client", lambda: StubClient())
    args = type(
        "Args",
        (),
        {"symbol": "AAPL", "side": "buy", "qty": "1", "time_in_force": "day", "confirm": True},
    )()

    exit_code = cmd_submit_order(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"id": "ord-1"' in captured.out
