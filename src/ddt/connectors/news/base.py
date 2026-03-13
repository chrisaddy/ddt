from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from ...models import NewsEvent


class NewsProvider(Protocol):
    name: str

    def fetch(self) -> Iterable[NewsEvent]:
        ...


@dataclass
class StaticNewsProvider:
    name: str
    events: list[NewsEvent]

    def fetch(self) -> Iterable[NewsEvent]:
        return self.events
