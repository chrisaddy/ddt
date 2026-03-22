"""JSONL-backed persistence for news events and trade proposals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from .config import get_settings


class JsonlStore:
    """Append-only store backed by a single ``.jsonl`` file.

    Creates the parent directory and the file itself on construction
    so callers never need to handle missing-path errors.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, item: Dict) -> None:
        """Append a single JSON object as a new line."""
        with self.path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(item) + '\n')

    def read_all(self) -> List[Dict]:
        """Read and parse every line, skipping blanks."""
        rows: List[Dict] = []
        with self.path.open('r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    def rewrite(self, items: Iterable[Dict]) -> None:
        """Replace the entire file contents with *items*."""
        with self.path.open('w', encoding='utf-8') as fh:
            for item in items:
                fh.write(json.dumps(item) + '\n')


def event_store() -> JsonlStore:
    """Return a :class:`JsonlStore` for persisted news events."""
    settings = get_settings()
    return JsonlStore(settings.state_dir / 'events.jsonl')


def proposal_store() -> JsonlStore:
    """Return a :class:`JsonlStore` for persisted trade proposals."""
    settings = get_settings()
    return JsonlStore(settings.state_dir / 'proposals.jsonl')
