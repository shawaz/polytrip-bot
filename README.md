# PolyTrip — Polymarket BTC 5-min Trading Bot

Auto-trading bot that predicts BTC price direction (up/down) in 5-minute windows on Polymarket, with a Next.js dashboard and Telegram notifications.

## Features

- **Two prediction strategies**: Technical indicators (RSI, MACD, Bollinger Bands) + ML (Gradient Boosting)
- **Live trading** on Polymarket CLOB with configurable risk per trade
- **Backtesting** over any historical date range with equity curve and performance metrics
- **Next.js dashboard**: start/stop bot, view trades, run backtests, configure settings
- **Telegram notifications** on every trade open/close and backtest completion

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your credentials:
# - Polymarket API key + private key (from polymarket.com)
# - Telegram bot token + chat ID
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

- **Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

### 3. Train the ML model (optional but recommended)

Open http://localhost:3000/settings and click **Train ML Model**, or via API:

```bash
curl -X POST "http://localhost:8000/api/predictor/train?days=30"
```

### 4. Start trading

Go to the dashboard, select a strategy, and click **Start Bot**.

---

## Architecture

```
polytrip/
├── backend/
│   ├── main.py               # FastAPI REST API
│   ├── trader.py             # Live trading loop (APScheduler, every 5 min)
│   ├── backtester.py         # Historical simulation engine
│   ├── predictor.py          # TechIndicator + ML + Ensemble predictors
│   ├── polymarket_client.py  # py-clob-client wrapper
│   ├── data_fetcher.py       # Binance 1-min OHLCV (no auth needed)
│   ├── telegram_notifier.py  # Trade + backtest Telegram alerts
│   ├── database.py           # SQLAlchemy + SQLite
│   └── models.py             # Trade, BacktestRun, BotConfig models
└── frontend/
    ├── app/page.tsx           # Dashboard
    ├── app/backtest/page.tsx  # Backtest control + results
    └── app/settings/page.tsx  # API keys, risk, strategy
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Bot status, open position, PnL |
| POST | `/api/bot/start` | Start live trading |
| POST | `/api/bot/stop` | Stop live trading |
| POST | `/api/backtest` | Run a backtest |
| GET | `/api/backtests` | List all backtest runs |
| GET | `/api/backtests/{id}` | Backtest detail with equity curve |
| GET | `/api/trades` | Trade history |
| GET | `/api/config` | Current config |
| PUT | `/api/config` | Update config |
| POST | `/api/predictor/train` | Train ML model |

## Getting Polymarket API Credentials

1. Go to [polymarket.com](https://polymarket.com) and connect a wallet
2. Go to Profile → API Keys → Create API Key
3. Your private key is your wallet's private key (keep safe!)

## Getting Telegram Credentials

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → get your **bot token**
2. Message [@userinfobot](https://t.me/userinfobot) → get your **chat ID**

---

> ⚠️ **Risk Warning**: Crypto trading involves significant risk. Use only funds you can afford to lose. This software is provided for educational purposes.
