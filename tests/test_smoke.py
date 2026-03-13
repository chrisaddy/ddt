from ddt.risk.rules import evaluate
from ddt.sample_data import sample_events
from ddt.strategies.news_reaction import HeadlineReactionStrategy


def test_sample_strategy_generates_proposals():
    strategy = HeadlineReactionStrategy()
    proposals = strategy.generate(sample_events())
    assert proposals
    assert any(p.symbol == 'NVDA' for p in proposals)


def test_risk_notes_present_for_un_sized_trade():
    strategy = HeadlineReactionStrategy()
    proposal = strategy.generate(sample_events())[0]
    notes = evaluate(proposal)
    assert 'position sizing missing' in notes
