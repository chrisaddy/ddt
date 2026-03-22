"""Lightweight risk-rule evaluation for trade proposals."""

from __future__ import annotations

from ..models import TradeProposal


def evaluate(proposal: TradeProposal) -> list[str]:
    """Return risk notes for *proposal* based on static rule checks."""
    notes: list[str] = []
    if proposal.confidence < 0.6:
        notes.append('confidence below live-trading threshold')
    if proposal.quantity_hint in {'', 'REVIEW_REQUIRED'}:
        notes.append('position sizing missing')
    if proposal.asset_class not in {'equity', 'crypto', 'future'}:
        notes.append('unsupported asset class')
    if proposal.side not in {'buy', 'sell'}:
        notes.append('invalid side')
    return notes
