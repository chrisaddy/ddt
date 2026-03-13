from __future__ import annotations

from ..store import proposal_store

VALID_TRANSITIONS = {
    'draft': {'approved', 'rejected'},
    'approved': {'submitted', 'rejected'},
    'submitted': {'filled', 'rejected'},
}


class ProposalNotFoundError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


def update_status(proposal_id: str, new_status: str) -> dict:
    store = proposal_store()
    proposals = store.read_all()
    updated = None
    for proposal in proposals:
        if proposal.get('proposal_id') != proposal_id:
            continue
        current = proposal.get('status', 'draft')
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise InvalidTransitionError(f'cannot transition {current} -> {new_status}')
        proposal['status'] = new_status
        updated = proposal
        break
    if updated is None:
        raise ProposalNotFoundError(proposal_id)
    store.rewrite(proposals)
    return updated
