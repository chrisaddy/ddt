from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import get_settings


@dataclass(frozen=True)
class GuardrailConfig:
    max_notional: float
    banned_symbols: list[str]
    enforce_market_hours: bool = True


def guardrail_config_from_settings() -> GuardrailConfig:
    settings = get_settings()
    return GuardrailConfig(
        max_notional=settings.max_order_notional,
        banned_symbols=settings.banned_symbols,
        enforce_market_hours=settings.enforce_market_hours,
    )


def evaluate_order_guardrails(preview: dict[str, Any], market: dict[str, Any], config: GuardrailConfig, open_orders: list[dict[str, Any]], market_is_open: bool = True) -> list[str]:
    notes: list[str] = []
    symbol = str(preview.get('symbol', '')).upper()
    side = str(preview.get('side', '')).lower()
    asset_class = str(preview.get('asset_class', 'equity')).lower()
    qty = float(preview.get('qty', 0) or 0)
    last_price = float(market.get('last_price', 0) or 0)
    notional = qty * last_price

    if symbol in {s.upper() for s in config.banned_symbols}:
        notes.append(f'banned symbol: {symbol}')
    if config.max_notional and notional > config.max_notional:
        notes.append(f'notional exceeds limit: {notional:.2f} > {config.max_notional:.2f}')
    if config.enforce_market_hours and asset_class == 'equity' and not market_is_open:
        notes.append('market is closed for equities')
    for order in open_orders:
        if str(order.get('symbol', '')).upper() == symbol and str(order.get('side', '')).lower() == side and str(order.get('status', '')).lower() not in {'canceled', 'filled', 'rejected'}:
            notes.append('duplicate open order exists')
            break
    if qty <= 0:
        notes.append('qty must be positive')
    if last_price <= 0:
        notes.append('missing market price')
    return notes
