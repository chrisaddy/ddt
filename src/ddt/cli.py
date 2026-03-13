from __future__ import annotations

import argparse
import json

from .approval.service import InvalidTransitionError, ProposalNotFoundError, update_status
from .config import get_settings, validate_alpaca_settings
from .connectors.alpaca.client import AlpacaClient
from .risk.rules import evaluate
from .sample_data import sample_events
from .store import event_store, proposal_store
from .strategies.news_reaction import HeadlineReactionStrategy


def _alpaca_client() -> AlpacaClient:
    validate_alpaca_settings(get_settings())
    return AlpacaClient()


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


def cmd_preview_order(args: argparse.Namespace) -> int:
    client = AlpacaClient(base_url='preview', api_key='preview', api_secret='preview')
    preview = client.preview_order(
        symbol=args.symbol,
        side=args.side,
        qty=args.qty,
        time_in_force=args.time_in_force,
        asset_class=args.asset_class,
    )
    print(json.dumps(preview, indent=2))
    return 0


def cmd_submit_order(args: argparse.Namespace) -> int:
    if not args.confirm:
        print('Refusing to submit without --confirm')
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
        'ingest-sample-news': cmd_ingest_sample_news,
        'list-events': cmd_list_events,
        'propose-trades': cmd_propose_trades,
        'list-proposals': cmd_list_proposals,
        'approve': cmd_approve,
        'preview-order': cmd_preview_order,
        'submit-order': cmd_submit_order,
    }
    for name, fn in simple_commands.items():
        sub = subparsers.add_parser(name)
        sub.set_defaults(func=fn)
        if name == 'approve':
            sub.add_argument('proposal_id')
        if name in {'preview-order', 'submit-order'}:
            sub.add_argument('--symbol', required=True)
            sub.add_argument('--side', required=True, choices=['buy', 'sell'])
            sub.add_argument('--qty', required=True)
            sub.add_argument('--time-in-force', default='day')
        if name == 'preview-order':
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
