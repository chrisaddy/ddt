"""Interactive Brokers Client Portal REST API client."""

from __future__ import annotations

from dataclasses import dataclass
import json
import ssl
from typing import Any, Callable, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ...config import get_settings

Transport = Callable[..., Any]


@dataclass
class IbkrClient:
    """Thin wrapper around the IBKR Client Portal Gateway API.

    Connects to a locally-running gateway (default ``localhost:5000``)
    and optionally disables SSL verification for self-signed certificates.
    """
    base_url: str | None = None
    account_id: str | None = None
    transport: Optional[Transport] = None
    verify_ssl: bool | None = None

    def __post_init__(self) -> None:
        settings = get_settings()
        if not self.base_url:
            self.base_url = settings.ibkr_base_url
        if not self.account_id:
            self.account_id = settings.ibkr_account_id
        if self.verify_ssl is None:
            self.verify_ssl = settings.ibkr_verify_ssl
        if self.transport is None:
            self.transport = urlopen

    def _ssl_context(self):
        if self.verify_ssl:
            return None
        return ssl._create_unverified_context()

    def _get(self, path: str, params: dict[str, Any] | None = None):
        assert self.base_url is not None
        if params:
            if path == '/iserver/marketdata/snapshot' and 'fields' in params:
                safe_params = dict(params)
                fields = safe_params.pop('fields')
                query = '?' + urlencode(safe_params) + f'&fields={fields}'
            else:
                query = f'?{urlencode(params)}'
        else:
            query = ''
        request = Request(f'{self.base_url}{path}{query}', headers={'Accept': 'application/json'}, method='GET')
        response = self.transport(request, timeout=10, context=self._ssl_context())
        return json.loads(response.read().decode('utf-8'))

    def config_summary(self) -> dict[str, str]:
        """Return a summary of the current client configuration."""
        return {
            'base_url': self.base_url or '',
            'account_id': self.account_id or '',
            'verify_ssl': str(bool(self.verify_ssl)),
        }

    def list_accounts(self):
        """List all linked brokerage accounts."""
        return self._get('/portfolio/accounts')

    def account_summary(self):
        """Fetch the account summary for the configured account."""
        assert self.account_id is not None
        return self._get(f'/portfolio/{self.account_id}/summary')

    def positions(self):
        """List open positions for the configured account."""
        assert self.account_id is not None
        return self._get(f'/portfolio/{self.account_id}/positions/0')

    def open_orders(self):
        """List all live (unfilled) orders."""
        return self._get('/iserver/account/orders')

    def search_contracts(self, symbol: str):
        """Search for contracts matching *symbol*."""
        return self._get('/iserver/secdef/search', params={'symbol': symbol.upper()})

    def contract_details(self, conid: str):
        """Fetch security definition details for a given contract ID."""
        return self._get('/iserver/secdef/info', params={'conid': conid})

    def market_snapshot(self, conid: str):
        """Fetch a real-time market data snapshot for a contract ID."""
        return self._get('/iserver/marketdata/snapshot', params={'conids': conid, 'fields': '31,84,85,86,88'})
