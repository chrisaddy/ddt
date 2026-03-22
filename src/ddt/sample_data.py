"""Synthetic sample data for local development and smoke tests."""

from .models import NewsEvent


def sample_events() -> list[NewsEvent]:
    """Return a small set of hard-coded news events for offline testing."""
    return [
        NewsEvent(source='sample', headline='NVDA wins major cloud partnership, shares surge after hours', summary='Synthetic sample event for local development.', url='https://example.com/nvda', tickers=['NVDA'], asset_classes=['equity']),
        NewsEvent(source='sample', headline='BTC ETF flows accelerate as crypto market sentiment improves', summary='Synthetic sample event for local development.', url='https://example.com/btc', tickers=['BTCUSD'], asset_classes=['crypto']),
        NewsEvent(source='sample', headline='TSLA faces new safety probe after delivery miss', summary='Synthetic sample event for local development.', url='https://example.com/tsla', tickers=['TSLA'], asset_classes=['equity']),
    ]
