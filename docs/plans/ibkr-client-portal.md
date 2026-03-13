# IBKR Client Portal Integration Plan

> For Hermes: use strict TDD for each task.

Goal: add an Interactive Brokers read-only integration path using Client Portal Gateway so ddt can eventually support futures and commodity workflows on a proper broker API.

Architecture: add a dedicated ibkr connector under src/ddt/connectors/ibkr using the local Client Portal Gateway HTTP API. Keep the first slice read-only: auth/config summary, account listing, and contract search for symbols like futures roots.

Tech Stack: Python stdlib only, urllib HTTPS requests, argparse, pytest.

---

Tasks
1. Add failing tests for IBKR config validation and local gateway summary
2. Add failing tests for account listing and contract search endpoints
3. Implement src/ddt/connectors/ibkr/client.py
4. Add CLI commands: ibkr-status, ibkr-accounts, ibkr-search-contracts
5. Update README with IBKR Client Portal setup notes
6. Run tests and commit
