"""Strategy protocol definition.

Every trading strategy must satisfy the :class:`Strategy` protocol by
exposing a ``name`` attribute and a :meth:`generate` method that turns
news events into trade proposals.
"""

from __future__ import annotations

from typing import Iterable, Protocol

from ..models import NewsEvent, TradeProposal


class Strategy(Protocol):
    """Protocol that all trading strategies must implement."""
    name: str

    def generate(self, events: Iterable[NewsEvent]) -> list[TradeProposal]:
        """Produce trade proposals from the given news events."""
        ...
