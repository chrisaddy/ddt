# ddt architecture

Goal: build a Hermes-centric command center that turns incoming market news into reviewable trade proposals, with explicit human approval before any order submission.

High-level flow
1. Ingest news or market events from approved sources
2. Normalize them into a common event schema
3. Extract tickers/themes and generate strategy-specific draft proposals
4. Run deterministic risk checks
5. Present proposals for manual approval
6. Only after approval, prepare or route an order to an execution adapter
7. Log every step for auditability and replay
