from __future__ import annotations

import argparse
import json

from .approval.service import InvalidTransitionError, ProposalNotFoundError, update_status
from .connectors.alpaca.client import AlpacaClient
from .risk.rules import evaluate
from .sample_data import sample_events
from .store import event_store, proposal_store
from .strategies.news_reaction import HeadlineReactionStrategy


def cmd_status(_: argparse.Namespace) -> int:
    client = AlpacaClient()
    print(json.dumps({'alpaca': client.config_summary()}, indent=2))
    return 0


def cmd_account(_: argparse.Namespace) -> int:
    client = AlpacaClient()
    print(json.dumps(client.get_account(), indent=2))
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
    commands = {'status': cmd_status, 'account': cmd_account, 'ingest-sample-news': cmd_ingest_sample_news, 'list-events': cmd_list_events, 'propose-trades': cmd_propose_trades, 'list-proposals': cmd_list_proposals, 'approve': cmd_approve}
    for name, fn in commands.items():
        sub = subparsers.add_parser(name)
        sub.set_defaults(func=fn)
        if name == 'approve':
            sub.add_argument('proposal_id')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
