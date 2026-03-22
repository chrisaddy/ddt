"""Alpaca Markets REST API client for trading and account management."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ...config import get_settings

Transport = Callable[..., Any]


@dataclass
class AlpacaClient:
    """Thin wrapper around the Alpaca v2 REST API.

    Credentials and base URL are loaded from :func:`~ddt.config.get_settings`
    when not supplied directly.  An optional *transport* callable allows
    tests to inject a fake HTTP layer.
    """
    base_url: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    transport: Optional[Transport] = None

    def __post_init__(self) -> None:
        settings = get_settings()
        if not self.base_url:
            self.base_url = settings.alpaca_base_url
        if not self.api_key:
            self.api_key = settings.alpaca_api_key
        if not self.api_secret:
            self.api_secret = settings.alpaca_api_secret
        if self.transport is None:
            self.transport = urlopen

    def config_summary(self) -> Dict[str, str]:
        """Return a redacted summary of the current client configuration."""
        return {
            'base_url': self.base_url or '',
            'api_key_present': str(bool(self.api_key)),
            'api_secret_present': str(bool(self.api_secret)),
        }

    def _headers(self) -> Dict[str, str]:
        return {
            'APCA-API-KEY-ID': self.api_key or '',
            'APCA-API-SECRET-KEY': self.api_secret or '',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
        assert self.base_url is not None
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = Request(f'{self.base_url}{path}', headers=self._headers(), data=data, method=method)
        response = self.transport(request, timeout=10)
        body = response.read().decode('utf-8')
        return json.loads(body)

    def _get(self, path: str) -> Any:
        return self._request('GET', path)

    def _post(self, path: str, payload: Dict[str, Any]) -> Any:
        return self._request('POST', path, payload)

    def get_account(self) -> Dict[str, Any]:
        """Fetch the trading account details."""
        return self._get('/v2/account')

    def get_positions(self) -> list[Dict[str, Any]]:
        """List all open positions."""
        return self._get('/v2/positions')

    def get_open_orders(self) -> list[Dict[str, Any]]:
        """List open orders sorted by most recent first."""
        query = urlencode({'status': 'open', 'direction': 'desc'})
        return self._get(f'/v2/orders?{query}')

    def get_clock(self) -> Dict[str, Any]:
        """Return the current market clock (open/close status and times)."""
        return self._get('/v2/clock')

    def preview_order(self, symbol: str, side: str, qty: str, time_in_force: str, asset_class: str = 'equity') -> Dict[str, Any]:
        """Build a local preview dict for an order without submitting it."""
        return {
            'symbol': symbol.upper(),
            'side': side,
            'qty': qty,
            'type': 'market',
            'time_in_force': time_in_force,
            'asset_class': asset_class,
            'status': 'preview_only',
            'warnings': [
                'manual review required',
                'submission requires explicit --confirm',
            ],
        }

    def submit_order(self, symbol: str, side: str, qty: str, time_in_force: str) -> Dict[str, Any]:
        """Submit a market order to Alpaca."""
        payload = {
            'symbol': symbol.upper(),
            'side': side,
            'type': 'market',
            'qty': qty,
            'time_in_force': time_in_force,
        }
        return self._post('/v2/orders', payload)
