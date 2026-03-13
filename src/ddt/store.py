from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from .config import get_settings


class JsonlStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, item: Dict) -> None:
        with self.path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(item) + '\n')

    def read_all(self) -> List[Dict]:
        rows: List[Dict] = []
        with self.path.open('r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    def rewrite(self, items: Iterable[Dict]) -> None:
        with self.path.open('w', encoding='utf-8') as fh:
            for item in items:
                fh.write(json.dumps(item) + '\n')


def event_store() -> JsonlStore:
    settings = get_settings()
    return JsonlStore(settings.state_dir / 'events.jsonl')


def proposal_store() -> JsonlStore:
    settings = get_settings()
    return JsonlStore(settings.state_dir / 'proposals.jsonl')
