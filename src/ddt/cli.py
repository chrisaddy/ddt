from __future__ import annotations

import argparse
import json

from .approval.service import InvalidTransitionError, ProposalNotFoundError, update_status
from .config import get_settings, validate_alpaca_settings, validate_polygon_settings
from .connectors.alpaca.client import AlpacaClient
from .connectors.polygon.client import PolygonClient
from .guardrails.orders import evaluate_order_guardrails, guardrail_config_from_settings
from .models import NewsEvent
from .news.normalize import normalize_polygon_news_item
from .risk.rules import evaluate
from .sample_data import sample_events
from .store import event_store, proposal_store
from .strategies.news_reaction import HeadlineReactionStrategy


def _alpaca_client() -> AlpacaClient:
    validate_alpaca_settings(get_settings())
    return AlpacaClient()


def _polygon_client() -> PolygonClient:
    validate_polygon_settings(get_settings())
    return PolygonClient()


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
    payload = _polygon_client().get_news(args.symbol, limit=args.limit)
    store = event_store()
    count = 0
    for item in payload.get('results', []):
        event = normalize_polygon_news_item(item)
        store.append(event.to_dict())
        count += 1
    print(f'ingested {count} polygon news events')
    return 0




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
    proposals = HeadlineReactionStrategy().generate(events)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='ddt')
    subparsers = parser.add_subparsers(dest='command', required=True)

    simple_commands = {
        'status': cmd_status,
        'account': cmd_account,
        'positions': cmd_positions,
        'orders': cmd_orders,
        'market-quote': cmd_market_quote,
        'ingest-sample-news': cmd_ingest_sample_news,
        'ingest-polygon-news': cmd_ingest_polygon_news,
        'list-events': cmd_list_events,
        'build-proposals-from-events': cmd_build_proposals_from_events,
        'propose-trades': cmd_propose_trades,
        'list-proposals': cmd_list_proposals,
        'approve': cmd_approve,
        'preview-order': cmd_preview_order,
        'submit-order': cmd_submit_order,
        'review-market': cmd_review_market,
    }
    for name, fn in simple_commands.items():
        sub = subparsers.add_parser(name)
        sub.set_defaults(func=fn)
        if name == 'approve':
            sub.add_argument('proposal_id')
        if name in {'market-quote'}:
            sub.add_argument('--symbol', required=True)
        if name in {'ingest-polygon-news', 'review-market', 'build-proposals-from-events'}:
            sub.add_argument('--symbol', required=False, default=None)
            sub.add_argument('--limit', type=int, default=5)
            if name == 'build-proposals-from-events':
                pass
        if name in {'preview-order', 'submit-order'}:
            sub.add_argument('--symbol', required=True)
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
