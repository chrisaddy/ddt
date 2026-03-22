"""News-driven discretionary trading CLI.

Provides configuration, data models, and persistence for ingesting news
events, generating trade proposals, and managing order workflows across
multiple broker connectors (Alpaca, Polygon, IBKR).
"""

__all__ = ['config', 'models', 'store']
