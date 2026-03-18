"""Proposal approval state machine.

Manages the lifecycle of a :class:`~ddt.models.TradeProposal` through its
allowed status transitions (draft -> approved -> submitted -> filled, with
rejection possible at every stage).
"""

from __future__ import annotations

from ..store import proposal_store

VALID_TRANSITIONS = {
    'draft': {'approved', 'rejected'},
    'approved': {'submitted', 'rejected'},
    'submitted': {'filled', 'rejected'},
}


class ProposalNotFoundError(Exception):
    """Raised when no proposal matches the given ID."""


class InvalidTransitionError(Exception):
    """Raised when a status transition violates :data:`VALID_TRANSITIONS`."""


def update_status(proposal_id: str, new_status: str) -> dict:
    """Transition a proposal to *new_status* and persist the change.

    Raises:
        ProposalNotFoundError: If *proposal_id* does not exist.
        InvalidTransitionError: If the transition is not allowed.
    """
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
