from __future__ import annotations

from ..models import NewsEvent

POSITIVE_WORDS = ('beats', 'surge', 'wins', 'approval', 'partnership', 'upgrade', 'record')
NEGATIVE_WORDS = ('misses', 'probe', 'cuts', 'fraud', 'delay', 'downgrade', 'lawsuit')
TAG_WORDS = {
    'earnings': ('earnings', 'beat', 'miss'),
    'partnership': ('partnership', 'deal'),
    'regulatory': ('probe', 'lawsuit', 'approval'),
    'analyst-upgrade': ('upgrade',),
    'analyst-downgrade': ('downgrade',),
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


def normalize_polygon_news_item(item: dict) -> NewsEvent:
    title = item.get('title', '')
    return NewsEvent(
        source='polygon',
        headline=title,
        summary=item.get('description', ''),
        url=item.get('article_url', ''),
        tickers=item.get('tickers', []),
        asset_classes=['equity'],
        metadata={
            'publisher': item.get('publisher', {}),
            'sentiment': infer_sentiment(title, item.get('insights')),
            'event_tags': infer_event_tags(title, item.get('keywords')),
            'insights': item.get('insights', []),
            'published_utc': item.get('published_utc'),
        },
    )
