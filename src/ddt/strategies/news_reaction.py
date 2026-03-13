from __future__ import annotations

from typing import Iterable, List

from ..models import NewsEvent, TradeProposal

POSITIVE = ('beats', 'surge', 'approval', 'wins', 'partnership', 'record', 'accelerate', 'improves', 'upgrade')
NEGATIVE = ('misses', 'probe', 'cuts', 'fraud', 'delay', 'downgrade', 'lawsuit')


class HeadlineReactionStrategy:
    name = 'headline_reaction'

    def _classify(self, event: NewsEvent) -> tuple[str | None, float]:
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

    def generate(self, events: Iterable[NewsEvent]) -> List[TradeProposal]:
        proposals: List[TradeProposal] = []
        for event in events:
            side, confidence = self._classify(event)
            if not side:
                continue
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
                        metadata={'event_tags': event.metadata.get('event_tags', []), 'sentiment': event.metadata.get('sentiment', 'neutral')},
                    )
                )
        return proposals
