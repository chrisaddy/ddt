"""JSONL-backed persistence layer for events and proposals.

Each store is a single ``.jsonl`` file where every line is a JSON object.
The module exposes two convenience constructors — :func:`event_store` and
:func:`proposal_store` — that point to the configured state directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from .config import get_settings


class JsonlStore:
    """Append-only (with rewrite) store backed by a single JSONL file."""
    def __init__(self, path: Path):
        """Initialise the store, creating the file and parent dirs if needed."""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, item: Dict) -> None:
        """Append a single JSON object as a new line."""
        with self.path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(item) + '\n')

    def read_all(self) -> List[Dict]:
        """Read every line and return a list of parsed dictionaries."""
        rows: List[Dict] = []
        with self.path.open('r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    def rewrite(self, items: Iterable[Dict]) -> None:
        """Overwrite the entire file with *items*."""
        with self.path.open('w', encoding='utf-8') as fh:
            for item in items:
                fh.write(json.dumps(item) + '\n')


def event_store() -> JsonlStore:
    """Return a :class:`JsonlStore` for ``events.jsonl``."""
    settings = get_settings()
    return JsonlStore(settings.state_dir / 'events.jsonl')


def proposal_store() -> JsonlStore:
    """Return a :class:`JsonlStore` for ``proposals.jsonl``."""
    settings = get_settings()
    return JsonlStore(settings.state_dir / 'proposals.jsonl')
