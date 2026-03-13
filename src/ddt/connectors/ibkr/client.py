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
        query = f'?{urlencode(params)}' if params else ''
        request = Request(f'{self.base_url}{path}{query}', headers={'Accept': 'application/json'}, method='GET')
        response = self.transport(request, timeout=10, context=self._ssl_context())
        return json.loads(response.read().decode('utf-8'))

    def config_summary(self) -> dict[str, str]:
        return {
            'base_url': self.base_url or '',
            'account_id': self.account_id or '',
            'verify_ssl': str(bool(self.verify_ssl)),
        }

    def list_accounts(self):
        return self._get('/portfolio/accounts')

    def search_contracts(self, symbol: str):
        return self._get('/iserver/secdef/search', params={'symbol': symbol.upper()})
