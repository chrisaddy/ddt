from __future__ import annotations

from typing import Iterable, Protocol

from ..models import NewsEvent, TradeProposal


class Strategy(Protocol):
    name: str

    def generate(self, events: Iterable[NewsEvent]) -> list[TradeProposal]:
        ...
