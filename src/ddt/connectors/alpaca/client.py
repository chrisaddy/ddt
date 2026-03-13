from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ...config import get_settings


@dataclass
class AlpacaClient:
    def config_summary(self) -> Dict[str, str]:
        settings = get_settings()
        return {
            'base_url': settings.alpaca_base_url,
            'api_key_present': str(bool(settings.alpaca_api_key)),
            'api_secret_present': str(bool(settings.alpaca_api_secret)),
        }

    def submit_order_preview(self, symbol: str, side: str, quantity_hint: str) -> Dict[str, str]:
        return {
            'symbol': symbol,
            'side': side,
            'quantity_hint': quantity_hint,
            'status': 'preview_only',
            'note': 'Execution adapter not implemented in scaffold.',
        }
