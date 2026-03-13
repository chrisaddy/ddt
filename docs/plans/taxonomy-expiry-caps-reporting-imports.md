# Taxonomy, Expiry, Caps, Reporting, and Safe Imports Plan

> For Hermes: use test-first implementation for every behavior in this plan.

Goal: improve signal quality and operational safety by expanding event taxonomy, expiring stale proposals, enforcing simple execution caps, exporting review reports, and allowing safe local import of user-provided news exports.

Architecture: keep enrichment logic in news modules, policy checks in guardrails, and workflow/reporting logic in CLI helpers. Use local files and JSONL so imported external content remains explicit, auditable, and user-controlled.

Tech Stack: Python stdlib, argparse, pathlib, json, csv, pytest.

---

## Task 1: Expand taxonomy tests
- Add tests for guidance raise/cut, M&A, product launch, legal/regulatory, macro sensitivity, analyst action tags.

## Task 2: Add stale-signal and cooldown tests
- Add tests ensuring proposals older than the configured TTL are marked stale/excluded from top ranking.
- Add tests for symbol cooldown windows after repeated proposals.

## Task 3: Add execution cap tests
- Add tests for daily per-symbol cap and max ranked proposals surfaced.

## Task 4: Add export/report tests
- Add tests for review-symbol and review-watchlist report export to local JSON files.

## Task 5: Add safe import tests
- Add tests for importing user-provided JSON exports into normalized events without web login automation.

## Task 6: Implement minimal code
- Extend normalize.py taxonomy and source metadata handling.
- Add ranking/filter helpers for expiry, cooldown, and caps.
- Add CLI export-report and import-news commands.

## Task 7: Verify and document
- Run focused tests, then full suite.
- Verify import/export commands locally.
