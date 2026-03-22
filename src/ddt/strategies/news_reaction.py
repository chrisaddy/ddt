"""Headline-reaction strategy: generates buy/sell proposals from news sentiment."""

from __future__ import annotations

from typing import Iterable, List

from ..models import NewsEvent, TradeProposal

POSITIVE = ('beats', 'surge', 'approval', 'wins', 'partnership', 'record', 'accelerate', 'improves', 'upgrade')
NEGATIVE = ('misses', 'probe', 'cuts', 'fraud', 'delay', 'downgrade', 'lawsuit')
EVENT_TAG_BONUS = {
    'earnings': 0.06,
    'partnership': 0.04,
    'analyst-upgrade': 0.03,
    'analyst-downgrade': 0.03,
    'regulatory': -0.02,
}


class HeadlineReactionStrategy:
    """Strategy that maps headline sentiment to directional trade proposals.

    Confidence is boosted or penalized by publisher credibility scores
    and semantic event tags (e.g. earnings, analyst upgrade).
    """

    name = 'headline_reaction'

    def _classify(self, event: NewsEvent) -> tuple[str | None, float]:
        """Classify an event as buy, sell, or skip with a base confidence."""
        sentiment = str(event.metadata.get('sentiment', '')).lower()
        if sentiment == 'positive':
            return 'buy', 0.62
        if sentiment == 'negative':
            return 'sell', 0.62
        headline = event.headline.lower()
        if any(word in headline for word in POSITIVE):
            return 'buy', 0.55
        if any(word in headline for word in NEGATIVE):
            return 'sell', 0.55
        return None, 0.0

    def _adjust_confidence(self, event: NewsEvent, base_confidence: float) -> float:
        """Adjust *base_confidence* using publisher score and event-tag bonuses."""
        score = float(event.metadata.get('source_score', 0.5) or 0.5)
        confidence = base_confidence + ((score - 0.5) * 0.2)
        for tag in event.metadata.get('event_tags', []):
            confidence += EVENT_TAG_BONUS.get(tag, 0.0)
        return max(0.0, min(0.95, round(confidence, 2)))

    def generate(self, events: Iterable[NewsEvent]) -> List[TradeProposal]:
        """Produce one proposal per (event, ticker) pair that has a clear signal."""
        proposals: List[TradeProposal] = []
        for event in events:
            side, base_confidence = self._classify(event)
            if not side:
                continue
            confidence = self._adjust_confidence(event, base_confidence)
            for ticker in event.tickers:
                proposals.append(
                    TradeProposal(
                        symbol=ticker,
                        side=side,
                        rationale=f'{self.name} matched event: {event.headline}',
                        confidence=confidence,
                        source_event_ids=[event.event_id],
                        asset_class=(event.asset_classes[0] if event.asset_classes else 'equity'),
                        quantity_hint='REVIEW_REQUIRED',
                        created_at=event.created_at,
                        metadata={
                            'event_tags': event.metadata.get('event_tags', []),
                            'sentiment': event.metadata.get('sentiment', 'neutral'),
                            'source_name': event.metadata.get('source_name', 'unknown'),
                            'source_score': event.metadata.get('source_score', 0.5),
                            'dedupe_key': event.metadata.get('dedupe_key', event.headline.lower()),
                        },
                    )
                )
        return proposals
