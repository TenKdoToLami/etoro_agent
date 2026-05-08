# eToro Agent — EYEBALL (SmoothDriftStrategy V2)

A standalone, modular, and professional trading bot that implements the **EYEBALL** momentum-capture strategy with drift-based rebalancing to manage an eToro Agent Portfolio.

The bot runs once per trading day, evaluates SPY market data and VIX levels, and maintains a multi-asset portfolio based on the current regime (Normal or Panic).

---

## Strategy Specification: EYEBALL

- **Two-Brain Logic**: Switches between NORMAL and PANIC modes.
- **Normal Mode (VIX < 43 & No Death Cross)**: 
    - 4x SPY: 65%
    - 3x SPY: 35%
- **Panic Mode (VIX >= 43 or Death Cross)**: 
    - GOLD: 60%
    - TLT: 25%
    - SHY: 10%
    - 4x SPY: 5%
- **Drift Tolerance**: 10% tolerance band for rebalancing.
- **Hysteresis**: 14-day wait period for maintenance rebalances.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — set symbols and ETORO_USER_KEY

# 3. Test connectivity
python -m etoro_bot status
python -m etoro_bot portfolio
```

---

## CLI Reference

Run commands with `python -m etoro_bot <command>`.

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Check if the US market is open today | `python -m etoro_bot status` |
| `portfolio` | Show equity, cash, and weights | `python -m etoro_bot portfolio` |
| `positions` | List all open manual positions | `python -m etoro_bot positions` |
| `run-job` | Execute the daily trading job | `python -m etoro_bot run-job --dry-run` |

---

## Configuration (`.env`)

| Variable | Description |
|----------|-------------|
| `ETORO_USER_KEY` | **Required.** Your agent-portfolio secret token |
| `SAFETY_CASH` | USD to keep uninvested to cover fees |
| `SYMBOL_4XSPY` | Symbol for the 4x Leveraged SPY proxy |
| `SYMBOL_3XSPY` | Symbol for the 3x Leveraged SPY proxy |
| `SYMBOL_GOLD` | Symbol for Gold (GLD) |
| `SYMBOL_TLT` | Symbol for Long-Term Bonds (TLT) |
| `SYMBOL_SHY` | Symbol for Short-Term Bonds (SHY) |

---

## Architecture

```
etoro_agent/
├── etoro_bot/           # Main Python package
│   ├── __main__.py      # python -m etoro_bot entry point
│   ├── cli.py           # CLI logic
│   ├── config.py        # Config loader
│   ├── daily_job.py     # Task orchestration
│   ├── core/            # Business logic
│   │   ├── engine.py    # Rebalancing engine
│   │   └── etoro.py     # eToro API client
│   ├── data/            # Data management
│   │   ├── market.py    # yfinance fetching
│   │   └── portfolio.py # Snapshots & Logs
│   ├── strategy/        # Strategy logic
│   │   ├── eyeball.py   # EYEBALL implementation
│   │   └── indicators.py
│   └── utils/           # Utilities
│       └── logger.py
├── scripts/             # Management scripts
│   ├── install.sh
│   └── uninstall.sh
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
