"""Base protocol for trade-proposal generation strategies."""

from __future__ import annotations

from typing import Iterable, Protocol

from ..models import NewsEvent, TradeProposal


class Strategy(Protocol):
    """Interface that all strategy implementations must satisfy."""
    name: str

    def generate(self, events: Iterable[NewsEvent]) -> list[TradeProposal]:
        """Produce trade proposals from a sequence of news events."""
        ...
