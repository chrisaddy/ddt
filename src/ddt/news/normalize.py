from __future__ import annotations

import re

from ..models import NewsEvent

POSITIVE_WORDS = ('beats', 'surge', 'wins', 'approval', 'partnership', 'upgrade', 'record')
NEGATIVE_WORDS = ('misses', 'probe', 'cuts', 'fraud', 'delay', 'downgrade', 'lawsuit')
TAG_WORDS = {
    'earnings': ('earnings', 'beat', 'miss'),
    'partnership': ('partnership',),
    'mna': ('acquisition', 'merger', 'buyout'),
    'product-launch': ('launches', 'launch', 'unveils', 'releases'),
    'regulatory': ('probe', 'lawsuit', 'approval', 'investigation'),
    'guidance-raise': ('raises guidance', 'guidance raised', 'boosts outlook'),
    'guidance-cut': ('cuts guidance', 'lowers guidance', 'reduces outlook'),
    'macro': ('tariff', 'inflation', 'rates', 'macro'),
    'analyst-upgrade': ('upgrade',),
    'analyst-downgrade': ('downgrade',),
}
PUBLISHER_SCORES = {
    'The Motley Fool': 0.62,
    'GlobeNewswire Inc.': 0.55,
    'Financial Times': 0.9,
    'The Economist': 0.86,
    'Bloomberg': 0.95,
}


def infer_sentiment(title: str, insights: list[dict] | None = None) -> str:
    if insights:
        sentiments = [str(item.get('sentiment', '')).lower() for item in insights if item.get('sentiment')]
        if 'positive' in sentiments:
            return 'positive'
        if 'negative' in sentiments:
            return 'negative'
    lowered = title.lower()
    if any(word in lowered for word in POSITIVE_WORDS):
        return 'positive'
    if any(word in lowered for word in NEGATIVE_WORDS):
        return 'negative'
    return 'neutral'


def infer_event_tags(title: str, keywords: list[str] | None = None) -> list[str]:
    lowered = title.lower()
    tags: list[str] = []
    for tag, patterns in TAG_WORDS.items():
        if any(pattern in lowered for pattern in patterns):
            tags.append(tag)
    for keyword in keywords or []:
        key = keyword.lower()
        if key == 'earnings' and 'earnings' not in tags:
            tags.append('earnings')
    return tags


def score_publisher(publisher: str) -> float:
    return PUBLISHER_SCORES.get(publisher, 0.5)


def dedupe_key(text: str) -> str:
    return re.sub(r'\W+', ' ', text.lower()).strip()


def normalize_polygon_news_item(item: dict) -> NewsEvent:
    title = item.get('title', '')
    publisher = item.get('publisher', {}) or {}
    source_name = publisher.get('name', 'unknown')
    return NewsEvent(
        source='polygon',
        headline=title,
        summary=item.get('description', ''),
        url=item.get('article_url', ''),
        tickers=item.get('tickers', []),
        asset_classes=['equity'],
        metadata={
            'publisher': publisher,
            'source_name': source_name,
            'source_score': score_publisher(source_name),
            'sentiment': infer_sentiment(title, item.get('insights')),
            'event_tags': infer_event_tags(title, item.get('keywords')),
            'dedupe_key': dedupe_key(title),
            'insights': item.get('insights', []),
            'published_utc': item.get('published_utc'),
        },
    )
