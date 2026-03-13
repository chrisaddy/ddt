# ddt

Hermes-native command center for news-driven discretionary trading workflows.

Status: scaffolded v1 for manual approval workflows.

What this repository is for
- Pull news from approved sources and normalize it into a common event model
- Extract entities, themes, and tickers from incoming news
- Generate draft trade proposals for human review
- Apply deterministic risk checks before any order can be prepared for submission
- Route approved orders to Alpaca only after explicit user approval

What this repository is not
- Autonomous live trading based on LLM judgment alone
- Credential-harvesting or automated login against subscription websites without an approved integration path

Quickstart
1. python3 -m venv .venv
2. source .venv/bin/activate
3. PYTHONPATH=src python3 -m ddt.cli status

Environment variables
- ALPACA_API_KEY
- ALPACA_API_SECRET
- ALPACA_BASE_URL
