from __future__ import annotations

import argparse
import json
from pathlib import Path

from .approval.service import InvalidTransitionError, ProposalNotFoundError, update_status
from .config import get_settings, validate_alpaca_settings, validate_polygon_settings, validate_ibkr_settings
from .connectors.alpaca.client import AlpacaClient
from .connectors.polygon.client import PolygonClient
from .connectors.ibkr.client import IbkrClient
from .guardrails.orders import evaluate_order_guardrails, guardrail_config_from_settings
from .models import NewsEvent
from .news.normalize import infer_event_tags, infer_sentiment, normalize_polygon_news_item, score_publisher, dedupe_key
from .risk.rules import evaluate
from .sample_data import sample_events
from .store import event_store, proposal_store
from .strategies.news_reaction import HeadlineReactionStrategy


STALE_AFTER_SECONDS = 7 * 24 * 3600
MAX_RANKED_PROPOSALS = 5
WATCHLIST_DAILY_CAP = 2



def _alpaca_client() -> AlpacaClient:
    validate_alpaca_settings(get_settings())
    return AlpacaClient()


def _polygon_client() -> PolygonClient:
    validate_polygon_settings(get_settings())
    return PolygonClient()


def _ibkr_client() -> IbkrClient:
    validate_ibkr_settings(get_settings())
    return IbkrClient()


def _latest_price(result: dict) -> float:
    payload = result.get('results', {})
    return float(payload.get('p', 0) or 0)


def _market_is_open(alpaca: AlpacaClient, asset_class: str) -> bool:
    if asset_class != 'equity':
        return True
    return bool(alpaca.get_clock().get('is_open', False))


def _guarded_preview(args: argparse.Namespace) -> dict:
    alpaca = _alpaca_client()
    polygon = _polygon_client()
    preview = alpaca.preview_order(
        symbol=args.symbol,
        side=args.side,
        qty=args.qty,
        time_in_force=args.time_in_force,
        asset_class=args.asset_class,
    )
    quote = polygon.get_last_trade(args.symbol)
    open_orders = alpaca.get_open_orders()
    notes = evaluate_order_guardrails(
        preview,
        market={'last_price': _latest_price(quote)},
        config=guardrail_config_from_settings(),
        open_orders=open_orders,
        market_is_open=_market_is_open(alpaca, args.asset_class),
    )
    preview['guardrail_notes'] = notes
    preview['market_price'] = _latest_price(quote)
    return preview






def cmd_ibkr_summary(_: argparse.Namespace) -> int:
    print(json.dumps(_ibkr_client().account_summary(), indent=2))
    return 0


def cmd_ibkr_positions(_: argparse.Namespace) -> int:
    print(json.dumps(_ibkr_client().positions(), indent=2))
    return 0


def cmd_ibkr_orders(_: argparse.Namespace) -> int:
    print(json.dumps(_ibkr_client().open_orders(), indent=2))
    return 0


def cmd_ibkr_contract_details(args: argparse.Namespace) -> int:
    print(json.dumps(_ibkr_client().contract_details(args.conid), indent=2))
    return 0


def cmd_ibkr_market_snapshot(args: argparse.Namespace) -> int:
    print(json.dumps(_ibkr_client().market_snapshot(args.conid), indent=2))
    return 0

def cmd_ibkr_status(_: argparse.Namespace) -> int:
    print(json.dumps({'ibkr': _ibkr_client().config_summary()}, indent=2))
    return 0


def cmd_ibkr_accounts(_: argparse.Namespace) -> int:
    print(json.dumps(_ibkr_client().list_accounts(), indent=2))
    return 0


def cmd_ibkr_search_contracts(args: argparse.Namespace) -> int:
    print(json.dumps(_ibkr_client().search_contracts(args.symbol), indent=2))
    return 0

def cmd_status(_: argparse.Namespace) -> int:
    client = _alpaca_client()
    print(json.dumps({'alpaca': client.config_summary()}, indent=2))
    return 0


def cmd_account(_: argparse.Namespace) -> int:
    client = _alpaca_client()
    print(json.dumps(client.get_account(), indent=2))
    return 0


def cmd_positions(_: argparse.Namespace) -> int:
    client = _alpaca_client()
    print(json.dumps(client.get_positions(), indent=2))
    return 0


def cmd_orders(_: argparse.Namespace) -> int:
    client = _alpaca_client()
    print(json.dumps(client.get_open_orders(), indent=2))
    return 0


def cmd_market_quote(args: argparse.Namespace) -> int:
    print(json.dumps(_polygon_client().get_last_trade(args.symbol), indent=2))
    return 0


def cmd_preview_order(args: argparse.Namespace) -> int:
    print(json.dumps(_guarded_preview(args), indent=2))
    return 0


def cmd_submit_order(args: argparse.Namespace) -> int:
    if not args.confirm:
        print('Refusing to submit without --confirm')
        return 1
    preview = _guarded_preview(args)
    if preview['guardrail_notes']:
        print(json.dumps({'error': 'order blocked by guardrails', 'preview': preview}, indent=2))
        return 1
    client = _alpaca_client()
    order = client.submit_order(
        symbol=args.symbol,
        side=args.side,
        qty=args.qty,
        time_in_force=args.time_in_force,
    )
    print(json.dumps(order, indent=2))
    return 0


def cmd_ingest_sample_news(_: argparse.Namespace) -> int:
    store = event_store()
    events = sample_events()
    for event in events:
        store.append(event.to_dict())
    print(f'ingested {len(events)} sample events')
    return 0


def cmd_ingest_polygon_news(args: argparse.Namespace) -> int:
    count = _ingest_polygon_news_for_symbol(args.symbol, args.limit)
    print(f'ingested {count} polygon news events')
    return 0


def _ingest_polygon_news_for_symbol(symbol: str, limit: int) -> int:
    payload = _polygon_client().get_news(symbol, limit=limit)
    store = event_store()
    count = 0
    for item in payload.get('results', []):
        event = normalize_polygon_news_item(item)
        store.append(event.to_dict())
        count += 1
    return count


def cmd_run_session(args: argparse.Namespace) -> int:
    symbols = [item.strip().upper() for item in args.symbols.split(',') if item.strip()]
    ingested = 0
    for symbol in symbols:
        ingested += _ingest_polygon_news_for_symbol(symbol, args.limit)
    rows = event_store().read_all()
    events = [_event_from_row(row) for row in rows]
    proposals_written = 0
    store = proposal_store()
    for symbol in symbols:
        symbol_events = [event for event in events if symbol in [ticker.upper() for ticker in event.tickers]]
        proposals = _build_proposals(symbol_events, symbol=symbol)
        for proposal in proposals:
            proposal.risk_notes = evaluate(proposal)
            store.append(proposal.to_dict())
            proposals_written += 1
    watchlist_args = type('Args', (), {
        'symbols': ','.join(symbols),
        'limit': args.limit,
        'side': args.side,
        'qty': args.qty,
        'time_in_force': args.time_in_force,
        'asset_class': args.asset_class,
    })()
    watchlist = json.loads(_capture_watchlist_json(watchlist_args))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(watchlist, indent=2), encoding='utf-8')
    print(f'session complete: ingested {ingested} events, wrote {proposals_written} proposals, report {output}')
    return 0


def _capture_watchlist_json(args: argparse.Namespace) -> str:
    symbols = [item.strip().upper() for item in args.symbols.split(',') if item.strip()]
    watchlist = []
    for symbol in symbols:
        symbol_args = type('Args', (), {
            'symbol': symbol,
            'limit': args.limit,
            'side': args.side,
            'qty': args.qty,
            'time_in_force': args.time_in_force,
            'asset_class': args.asset_class,
        })()
        payload = _review_symbol_payload(symbol_args)
        notes = []
        if len(payload.get('ranked_proposals', [])) > WATCHLIST_DAILY_CAP:
            notes.append(f'cap: more than {WATCHLIST_DAILY_CAP} ranked proposals for symbol')
        if any((item.get('metadata', {}) or {}).get('agreement_count', 0) <= 1 for item in payload.get('ranked_proposals', [])[:1]):
            notes.append('cooldown: low confirmation / single-source top signal')
        watchlist.append({
            'symbol': symbol,
            'top_proposal': payload.get('top_proposal'),
            'proposal_count': len(payload.get('ranked_proposals', [])),
            'policy_notes': notes,
            'preview': payload.get('preview'),
        })
    watchlist.sort(key=lambda item: (item['top_proposal'] or {}).get('metadata', {}).get('ranking_score', -1), reverse=True)
    return json.dumps({'watchlist': watchlist})










def _parse_iso(ts: str) -> float:
    from datetime import datetime
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0.0


def _rank_proposal_dicts(proposals: list[dict]) -> list[dict]:
    if not proposals:
        return []
    agreement = {}
    recency = {}
    now = max((_parse_iso(p.get('created_at', '')) for p in proposals), default=0.0)
    for proposal in proposals:
        key = (proposal['symbol'].upper(), proposal['side'].lower(), proposal.get('metadata', {}).get('dedupe_key', ''))
        agreement[key] = agreement.get(key, 0) + 1
        recency[key] = max(recency.get(key, 0.0), _parse_iso(proposal.get('created_at', '')))
    newest = max(recency.values()) if recency else 0.0
    ranked = []
    for proposal in proposals:
        key = (proposal['symbol'].upper(), proposal['side'].lower(), proposal.get('metadata', {}).get('dedupe_key', ''))
        age_seconds = max(0.0, now - recency[key]) if now else 0.0
        is_stale = age_seconds > STALE_AFTER_SECONDS
        age_penalty = min(0.25, age_seconds / 86400.0 * 0.01) if now else 0.0
        stale_penalty = 0.2 if is_stale else 0.0
        ranking_score = round(proposal.get('confidence', 0.0) + (agreement[key] - 1) * 0.05 - age_penalty - stale_penalty, 2)
        proposal = dict(proposal)
        metadata = dict(proposal.get('metadata', {}))
        metadata['agreement_count'] = agreement[key]
        metadata['ranking_score'] = ranking_score
        metadata['is_stale'] = is_stale
        proposal['metadata'] = metadata
        ranked.append(proposal)
    ranked.sort(key=lambda p: p['metadata']['ranking_score'], reverse=True)
    return ranked[:MAX_RANKED_PROPOSALS]


def _review_symbol_payload(args: argparse.Namespace) -> dict:
    rows = event_store().read_all()
    events = [_event_from_row(row) for row in rows]
    symbol = args.symbol.upper()
    matching_events = [event for event in events if symbol in [ticker.upper() for ticker in event.tickers]]
    raw_proposals = _raw_proposals(matching_events, symbol=symbol)
    ranked_proposals = _rank_proposal_dicts([proposal.to_dict() for proposal in raw_proposals])
    proposal_dicts = _dedupe_proposals(raw_proposals)
    proposal_dicts = [proposal.to_dict() for proposal in proposal_dicts]
    preview = _guarded_preview(args)
    return {
        'symbol': symbol,
        'quote': _polygon_client().get_last_trade(symbol),
        'recent_news': _polygon_client().get_news(symbol, limit=args.limit).get('results', []),
        'stored_events': [event.to_dict() for event in matching_events],
        'generated_proposals': proposal_dicts,
        'ranked_proposals': ranked_proposals,
        'top_proposal': ranked_proposals[0] if ranked_proposals else None,
        'preview': preview,
    }

def _refresh_event_metadata(event: NewsEvent) -> NewsEvent:
    publisher = event.metadata.get('publisher', {}) or {}
    source_name = publisher.get('name', event.metadata.get('source_name', 'unknown'))
    metadata = dict(event.metadata)
    metadata['source_name'] = source_name
    metadata['source_score'] = score_publisher(source_name)
    metadata['sentiment'] = infer_sentiment(event.headline, metadata.get('insights'))
    metadata['event_tags'] = infer_event_tags(event.headline, metadata.get('keywords'))
    metadata['dedupe_key'] = dedupe_key(event.headline)
    event.metadata = metadata
    return event


def cmd_backfill_event_metadata(_: argparse.Namespace) -> int:
    store = event_store()
    rows = store.read_all()
    updated_rows = []
    count = 0
    for row in rows:
        event = _event_from_row(row)
        before = dict(event.metadata)
        event = _refresh_event_metadata(event)
        updated_rows.append(event.to_dict())
        if event.metadata != before:
            count += 1
    store.rewrite(updated_rows)
    print(f'updated {count} events')
    return 0

def _raw_proposals(events: list[NewsEvent], symbol: str | None = None) -> list:
    proposals = HeadlineReactionStrategy().generate(events)
    if symbol:
        symbol = symbol.upper()
        proposals = [proposal for proposal in proposals if proposal.symbol.upper() == symbol]
    return proposals


def _build_proposals(events: list[NewsEvent], symbol: str | None = None) -> list:
    return _dedupe_proposals(_raw_proposals(events, symbol=symbol))



def _dedupe_proposals(proposals: list) -> list:
    deduped = []
    seen = set()
    for proposal in proposals:
        key = (proposal.symbol.upper(), proposal.side.lower(), proposal.metadata.get('dedupe_key', proposal.rationale.lower()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(proposal)
    return deduped

def _event_from_row(row: dict) -> NewsEvent:
    return NewsEvent(
        source=row.get('source', ''),
        headline=row.get('headline', ''),
        summary=row.get('summary', ''),
        url=row.get('url', ''),
        tickers=row.get('tickers', []),
        asset_classes=row.get('asset_classes', []),
        event_id=row.get('event_id', ''),
        created_at=row.get('created_at', ''),
        metadata=row.get('metadata', {}),
    )


def cmd_build_proposals_from_events(args: argparse.Namespace) -> int:
    rows = event_store().read_all()
    events = [_event_from_row(row) for row in rows]
    if args.symbol:
        symbol = args.symbol.upper()
        events = [event for event in events if symbol in [ticker.upper() for ticker in event.tickers]]
    proposals = _build_proposals(events, symbol=args.symbol)
    store = proposal_store()
    for proposal in proposals:
        proposal.risk_notes = evaluate(proposal)
        store.append(proposal.to_dict())
        print(json.dumps(proposal.to_dict(), indent=2))
    return 0

def cmd_list_events(_: argparse.Namespace) -> int:
    for row in event_store().read_all():
        print(json.dumps(row, indent=2))
    return 0


def cmd_propose_trades(_: argparse.Namespace) -> int:
    events = sample_events()
    strategy = HeadlineReactionStrategy()
    proposals = strategy.generate(events)
    store = proposal_store()
    for proposal in proposals:
        proposal.risk_notes = evaluate(proposal)
        store.append(proposal.to_dict())
        print(json.dumps(proposal.to_dict(), indent=2))
    return 0


def cmd_list_proposals(_: argparse.Namespace) -> int:
    for row in proposal_store().read_all():
        print(json.dumps(row, indent=2))
    return 0




def cmd_review_symbol(args: argparse.Namespace) -> int:
    print(json.dumps(_review_symbol_payload(args), indent=2))
    return 0


def cmd_review_watchlist(args: argparse.Namespace) -> int:
    print(json.dumps(json.loads(_capture_watchlist_json(args)), indent=2))
    return 0

def cmd_review_market(args: argparse.Namespace) -> int:
    alpaca = _alpaca_client()
    polygon = _polygon_client()
    summary = {
        'account': alpaca.get_account(),
        'positions': alpaca.get_positions(),
        'open_orders': alpaca.get_open_orders(),
        'news': polygon.get_news(args.symbol, limit=args.limit).get('results', []),
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    try:
        updated = update_status(args.proposal_id, 'approved')
    except (ProposalNotFoundError, InvalidTransitionError) as exc:
        print(str(exc))
        return 1
    print(json.dumps(updated, indent=2))
    return 0




def cmd_export_review_report(args: argparse.Namespace) -> int:
    if args.mode == 'symbol':
        payload = _review_symbol_payload(args)
    else:
        payload = {'watchlist': []}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'wrote report to {output}')
    return 0


def cmd_import_news_json(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.input).read_text(encoding='utf-8'))
    store = event_store()
    count = 0
    for item in rows:
        event = normalize_polygon_news_item(item)
        if args.source:
            event.source = args.source
        store.append(event.to_dict())
        count += 1
    print(f'imported {count} news events')
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='ddt')
    subparsers = parser.add_subparsers(dest='command', required=True)

    simple_commands = {
        'status': cmd_status,
        'ibkr-status': cmd_ibkr_status,
        'ibkr-accounts': cmd_ibkr_accounts,
        'ibkr-summary': cmd_ibkr_summary,
        'ibkr-positions': cmd_ibkr_positions,
        'ibkr-orders': cmd_ibkr_orders,
        'ibkr-search-contracts': cmd_ibkr_search_contracts,
        'ibkr-contract-details': cmd_ibkr_contract_details,
        'ibkr-market-snapshot': cmd_ibkr_market_snapshot,
        'account': cmd_account,
        'positions': cmd_positions,
        'orders': cmd_orders,
        'market-quote': cmd_market_quote,
        'ingest-sample-news': cmd_ingest_sample_news,
        'ingest-polygon-news': cmd_ingest_polygon_news,
        'backfill-event-metadata': cmd_backfill_event_metadata,
        'list-events': cmd_list_events,
        'build-proposals-from-events': cmd_build_proposals_from_events,
        'propose-trades': cmd_propose_trades,
        'list-proposals': cmd_list_proposals,
        'approve': cmd_approve,
        'preview-order': cmd_preview_order,
        'submit-order': cmd_submit_order,
        'review-market': cmd_review_market,
        'review-symbol': cmd_review_symbol,
        'review-watchlist': cmd_review_watchlist,
        'export-review-report': cmd_export_review_report,
        'import-news-json': cmd_import_news_json,
        'run-session': cmd_run_session,
    }
    for name, fn in simple_commands.items():
        sub = subparsers.add_parser(name)
        sub.set_defaults(func=fn)
        if name == 'approve':
            sub.add_argument('proposal_id')
        if name in {'market-quote', 'ibkr-search-contracts'}:
            sub.add_argument('--symbol', required=True)
        if name in {'ibkr-contract-details', 'ibkr-market-snapshot'}:
            sub.add_argument('--conid', required=True)
        if name in {'ingest-polygon-news', 'review-market', 'build-proposals-from-events'}:
            sub.add_argument('--symbol', required=False, default=None)
            sub.add_argument('--limit', type=int, default=5)
        if name == 'review-symbol':
            sub.add_argument('--limit', type=int, default=5)
        if name == 'review-watchlist':
            sub.add_argument('--symbols', required=True)
            sub.add_argument('--limit', type=int, default=5)
        if name == 'export-review-report':
            sub.add_argument('--mode', required=True, choices=['symbol'])
            sub.add_argument('--output', required=True)
            sub.add_argument('--symbol', required=True)
            sub.add_argument('--limit', type=int, default=5)
        if name == 'import-news-json':
            sub.add_argument('--input', required=True)
            sub.add_argument('--source', default='imported-json')
        if name == 'run-session':
            sub.add_argument('--symbols', required=True)
            sub.add_argument('--limit', type=int, default=5)
            sub.add_argument('--output', required=True)
        if name in {'preview-order', 'submit-order', 'review-symbol'}:
            sub.add_argument('--symbol', required=True)
            sub.add_argument('--side', required=True, choices=['buy', 'sell'])
            sub.add_argument('--qty', required=True)
            sub.add_argument('--time-in-force', default='day')
            sub.add_argument('--asset-class', default='equity', choices=['equity', 'crypto', 'future'])
        if name in {'review-watchlist', 'export-review-report', 'run-session'}:
            sub.add_argument('--side', required=True, choices=['buy', 'sell'])
            sub.add_argument('--qty', required=True)
            sub.add_argument('--time-in-force', default='day')
            sub.add_argument('--asset-class', default='equity', choices=['equity', 'crypto', 'future'])
        if name == 'submit-order':
            sub.add_argument('--confirm', action='store_true')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
