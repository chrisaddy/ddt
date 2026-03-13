from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class NewsEvent:
    source: str
    headline: str
    summary: str
    url: str
    tickers: List[str] = field(default_factory=list)
    asset_classes: List[str] = field(default_factory=list)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TradeProposal:
    symbol: str
    side: str
    rationale: str
    confidence: float
    source_event_ids: List[str]
    asset_class: str = 'equity'
    quantity_hint: str = ''
    status: str = 'draft'
    proposal_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    risk_notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
