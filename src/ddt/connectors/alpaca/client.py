from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Dict, Optional
from urllib.request import Request, urlopen

from ...config import get_settings

Transport = Callable[..., Any]


@dataclass
class AlpacaClient:
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
        }

    def _get(self, path: str) -> Dict[str, Any]:
        assert self.base_url is not None
        request = Request(f"{self.base_url}{path}", headers=self._headers(), method='GET')
        response = self.transport(request, timeout=10)
        payload = response.read().decode('utf-8')
        return json.loads(payload)

    def get_account(self) -> Dict[str, Any]:
        return self._get('/v2/account')

    def submit_order_preview(self, symbol: str, side: str, quantity_hint: str) -> Dict[str, str]:
        return {
            'symbol': symbol,
            'side': side,
            'quantity_hint': quantity_hint,
            'status': 'preview_only',
            'note': 'Execution adapter not implemented in scaffold.',
        }
