# eToro Agent — V9 Intra Daily Trading Bot

A standalone, modular, and professional trading bot that uses the **Genome V9 Intra-Day
Confidence** neural-net strategy to manage an eToro Agent Portfolio.

The bot runs once per trading day (typically 17:00 Prague time), evaluates
SPY market data through the trained genome, and maps the output state
(`CASH / SPY / 2xSPY / 3xSPY`) to real eToro positions.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — at minimum set ETORO_USER_KEY

# 3. Test connectivity
python -m etoro_bot status
python -m etoro_bot portfolio
```

---

## CLI Reference

Run commands with `python -m etoro_bot <command>`.

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Check if the US market is open today (via yfinance) | `python -m etoro_bot status` |
| `portfolio` | Show equity, cash, and invested totals | `python -m etoro_bot portfolio` |
| `positions` | List all open manual positions | `python -m etoro_bot positions` |
| `buy` | Manually open a position | `python -m etoro_bot buy --symbol SPY --amount 500` |
| `sell` | Manually close a position by ID | `python -m etoro_bot sell --id 12345678` |
| `run-job` | Execute the full daily trading job | `python -m etoro_bot run-job` |

---

## Configuration (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ETORO_API_KEY` | *(pre-filled)* | eToro platform API key (rarely changes) |
| `ETORO_USER_KEY` | — | **Required.** Your agent-portfolio secret token |
| `SAFETY_CASH` | `20` | USD to always keep uninvested to cover fees |
| `MIN_POSITION_VALUE` | `40` | Minimum USD to justify opening a new position |
| `GENOME_PATH` | `./genome.json` | Path to the V9 Intra genome JSON |
| `SYMBOL_CASH` | `BND` | ETF to hold when strategy says CASH (bonds) |
| `SYMBOL_SPY` | `SPY` | Symbol for the 1× state |
| `SYMBOL_2XSPY` | `SSO` | Symbol for the 2× state |
| `SYMBOL_3XSPY` | `UPRO` | Symbol for the 3× state |
| `DB_PATH` | `./data.sqlite` | SQLite path for market OHLCV data |
| `PORTFOLIO_DB_PATH` | `./portfolio.sqlite` | SQLite path for daily portfolio snapshots |

---

## Cron Scheduling

```bash
# Install (adds 17:00 Mon–Fri cron entry)
chmod +x scripts/install.sh && ./scripts/install.sh

# Remove
chmod +x scripts/uninstall.sh && ./scripts/uninstall.sh

# Verify
crontab -l
```

---

## Architecture

```
etoro_agent/
├── etoro_bot/           # Main Python package
│   ├── __init__.py
│   ├── __main__.py      # python -m etoro_bot entry point
│   ├── cli.py           # CLI logic
│   ├── config.py        # Config loader
│   ├── daily_job.py     # Task orchestration
│   ├── core/            # Business logic
│   │   ├── engine.py    # Trading logic
│   │   └── etoro.py     # eToro API client
│   ├── data/            # Data management
│   │   ├── market.py    # yfinance fetching
│   │   └── portfolio.py # Portfolio snapshots
│   ├── strategy/        # Neural-net logic
│   │   ├── v9_intra.py
│   │   └── indicators.py
│   └── utils/           # Utilities
│       └── logger.py
├── scripts/             # Management scripts
│   ├── install.sh
│   └── uninstall.sh
├── genome.json
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
