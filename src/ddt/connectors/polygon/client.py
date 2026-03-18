"""Polygon.io market-data connector.

Provides last-trade lookups (with a previous-close fallback) and
news retrieval from the Polygon REST API.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ...config import get_settings

Transport = Callable[..., Any]


@dataclass
class PolygonClient:
    """HTTP client for the Polygon.io REST API."""
    base_url: str | None = None
    api_key: str | None = None
    transport: Optional[Transport] = None

    def __post_init__(self) -> None:
        settings = get_settings()
        if not self.base_url:
            self.base_url = settings.polygon_base_url
        if not self.api_key:
            self.api_key = settings.polygon_api_key
        if self.transport is None:
            self.transport = urlopen

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        assert self.base_url is not None
        query = params.copy() if params else {}
        query['apiKey'] = self.api_key or ''
        url = f'{self.base_url}{path}?{urlencode(query)}'
        request = Request(url, headers={'Accept': 'application/json'}, method='GET')
        response = self.transport(request, timeout=10)
        return json.loads(response.read().decode('utf-8'))

    def get_last_trade(self, symbol: str) -> dict[str, Any]:
        """Fetch the last trade for *symbol*, falling back to previous close."""
        symbol = symbol.upper()
        try:
            return self._get(f'/v2/last/trade/{symbol}')
        except HTTPError as exc:
            if exc.code not in {401, 403, 404}:
                raise
            prev = self._get(f'/v2/aggs/ticker/{symbol}/prev')
            results = prev.get('results', [])
            close_price = results[0].get('c', 0) if results else 0
            return {'results': {'T': symbol, 'p': close_price, 'source': 'prev_close_fallback'}}

    def get_news(self, symbol: str | None = None, limit: int = 10) -> dict[str, Any]:
        """Fetch recent news articles, optionally filtered by *symbol*."""
        params = {'limit': limit}
        if symbol:
            params['ticker'] = symbol.upper()
        return self._get('/v2/reference/news', params=params)
