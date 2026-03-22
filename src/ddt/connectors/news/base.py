"""Protocol and static implementation for pluggable news providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from ...models import NewsEvent


class NewsProvider(Protocol):
    """Interface that all news provider backends must satisfy."""
    name: str

    def fetch(self) -> Iterable[NewsEvent]:
        """Yield news events from this provider."""
        ...


@dataclass
class StaticNewsProvider:
    """In-memory news provider that returns a fixed list of events."""
    name: str
    events: list[NewsEvent]

    def fetch(self) -> Iterable[NewsEvent]:
        """Return the pre-loaded events."""
        return self.events
