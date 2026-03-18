"""News provider protocol and static implementation.

Defines the :class:`NewsProvider` protocol that all news sources must
satisfy, plus a :class:`StaticNewsProvider` for testing and local
development.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from ...models import NewsEvent


class NewsProvider(Protocol):
    """Protocol for objects that supply news events."""
    name: str

    def fetch(self) -> Iterable[NewsEvent]:
        """Retrieve news events from the provider."""
        ...


@dataclass
class StaticNewsProvider:
    """A news provider backed by a fixed list of events."""
    name: str
    events: list[NewsEvent]

    def fetch(self) -> Iterable[NewsEvent]:
        """Return the pre-loaded events."""
        return self.events
