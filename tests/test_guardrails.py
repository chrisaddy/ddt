import pytest

from ddt.guardrails.orders import GuardrailConfig, evaluate_order_guardrails


def test_guardrails_block_notional_over_limit():
    config = GuardrailConfig(max_notional=100.0, banned_symbols=[])
    preview = {"symbol": "AAPL", "side": "buy", "qty": "2"}
    market = {"last_price": 75.0}

    notes = evaluate_order_guardrails(preview, market=market, config=config, open_orders=[])

    assert 'notional exceeds limit' in notes[0].lower()


def test_guardrails_block_banned_symbol_and_duplicate_open_order():
    config = GuardrailConfig(max_notional=1000.0, banned_symbols=['GME'])
    preview = {"symbol": "GME", "side": "buy", "qty": "1"}
    market = {"last_price": 20.0}
    open_orders = [{"symbol": "GME", "side": "buy", "status": "new"}]

    notes = evaluate_order_guardrails(preview, market=market, config=config, open_orders=open_orders)

    assert any('banned symbol' in note.lower() for note in notes)
    assert any('duplicate open order' in note.lower() for note in notes)


def test_guardrails_block_outside_market_hours_for_equities():
    config = GuardrailConfig(max_notional=1000.0, banned_symbols=[], enforce_market_hours=True)
    preview = {"symbol": "AAPL", "side": "buy", "qty": "1", "asset_class": "equity"}
    market = {"last_price": 20.0}

    notes = evaluate_order_guardrails(
        preview,
        market=market,
        config=config,
        open_orders=[],
        market_is_open=False,
    )

    assert any('market is closed' in note.lower() for note in notes)
