# ddt

Hermes-native command center for news-driven discretionary trading workflows.

Status: manual-approval trading command center with Alpaca account/order plumbing, Polygon market/news reads, and deterministic order guardrails.

What this repository is for
- Pull market news into a common event model
- Read account, positions, orders, quotes, and recent news
- Generate draft trade proposals for human review
- Apply deterministic guardrails before order submission
- Keep Hermes as the review and command-center layer

What this repository is not
- Autonomous live trading based on model judgment alone
- Credential-harvesting or automated login against subscription sites without an approved integration path

Quickstart
1. python3 -m venv .venv
2. source .venv/bin/activate
3. source .envrc
4. PYTHONPATH=src python3 -m ddt.cli status

Environment variables
- ALPACA_API_KEY or ALPACA_KEY_ID
- ALPACA_API_SECRET or ALPACA_SECRET_KEY
- ALPACA_BASE_URL
- ALPACA_DATA_URL
- POLYGON_API_KEY
- POLYGON_BASE_URL (optional)
- DDT_MAX_ORDER_NOTIONAL (optional, default 250)
- DDT_BANNED_SYMBOLS (optional comma-separated)
- DDT_ENFORCE_MARKET_HOURS (optional, default true)

Useful commands
- PYTHONPATH=src python3 -m ddt.cli account
- PYTHONPATH=src python3 -m ddt.cli positions
- PYTHONPATH=src python3 -m ddt.cli orders
- PYTHONPATH=src python3 -m ddt.cli market-quote --symbol AAPL
- PYTHONPATH=src python3 -m ddt.cli ingest-polygon-news --symbol AAPL --limit 5
- PYTHONPATH=src python3 -m ddt.cli review-market --symbol AAPL --limit 5
- PYTHONPATH=src python3 -m ddt.cli preview-order --symbol AAPL --side buy --qty 1 --time-in-force day --asset-class equity
- PYTHONPATH=src python3 -m ddt.cli submit-order --symbol AAPL --side buy --qty 1 --time-in-force day --asset-class equity --confirm

IBKR Client Portal setup
- Run IBKR Client Portal Gateway or IB Gateway/TWS-compatible local HTTP bridge
- Set IBKR_BASE_URL (default https://localhost:5000/v1/api)
- Set IBKR_ACCOUNT_ID
- Optionally set IBKR_VERIFY_SSL=false for local self-signed gateway certs
- Commands:
  - PYTHONPATH=src python3 -m ddt.cli ibkr-status
  - PYTHONPATH=src python3 -m ddt.cli ibkr-accounts
  - PYTHONPATH=src python3 -m ddt.cli ibkr-search-contracts --symbol CL
