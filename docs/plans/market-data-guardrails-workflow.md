# Market Data, Guardrails, and Workflow Implementation Plan

> For Hermes: use test-first implementation for every behavior added here.

Goal: add deterministic order guardrails, Polygon market/news connectors, and a command-center workflow command that summarizes the trading state without making autonomous trade decisions.

Architecture: keep transport adapters thin and deterministic, put policy logic in a dedicated guardrails module, and expose everything through explicit CLI commands. Use local JSONL persistence for ingested news so Hermes can replay and review events.

Tech Stack: Python stdlib only, urllib for HTTP, argparse for CLI, pytest for tests, JSONL local storage.

---

## Task 1: Add failing tests for guardrails
- Test max notional enforcement
- Test banned symbols enforcement
- Test duplicate open-order rejection
- Test market-hours policy checks

## Task 2: Add failing tests for Polygon integration
- Test snapshot/last trade quote endpoint wiring
- Test Polygon news endpoint wiring
- Test CLI output for market and news commands

## Task 3: Add failing tests for news ingestion + workflow
- Test persisted news ingestion from Polygon connector
- Test review-market workflow output structure
- Test preview-order guardrail notes

## Task 4: Implement minimal production code
- Add config for Polygon and guardrail env values
- Add Polygon client
- Add order guardrails module
- Extend CLI with market, news, ingest-polygon-news, review-market, guarded-preview-order

## Task 5: Verify and document
- Run targeted tests, then full suite
- Source .envrc and verify live read-only commands
- Update README with new commands
