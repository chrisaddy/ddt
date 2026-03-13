from __future__ import annotations

from typing import Iterable, List

from ..models import NewsEvent, TradeProposal

POSITIVE = ('beats', 'surge', 'approval', 'wins', 'partnership', 'record', 'accelerate', 'improves')
NEGATIVE = ('misses', 'probe', 'cuts', 'fraud', 'delay', 'downgrade')


class HeadlineReactionStrategy:
    name = 'headline_reaction'

    def generate(self, events: Iterable[NewsEvent]) -> List[TradeProposal]:
        proposals: List[TradeProposal] = []
        for event in events:
            headline = event.headline.lower()
            side = None
            confidence = 0.0
            if any(word in headline for word in POSITIVE):
                side = 'buy'
                confidence = 0.55
            elif any(word in headline for word in NEGATIVE):
                side = 'sell'
                confidence = 0.55
            if not side:
                continue
            for ticker in event.tickers:
                proposals.append(TradeProposal(symbol=ticker, side=side, rationale=f'{self.name} matched headline: {event.headline}', confidence=confidence, source_event_ids=[event.event_id], asset_class=(event.asset_classes[0] if event.asset_classes else 'equity'), quantity_hint='REVIEW_REQUIRED'))
        return proposals
