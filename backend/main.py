"""
PolyTrip Backend — FastAPI application.

Provides REST API for the Next.js dashboard to control
the Polymarket BTC 5-min trading bot.
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backtester import run_backtest
from config import settings
from database import SessionLocal, get_db, init_db
from models import BacktestRun, BotConfig, Trade
from polymarket_client import PolymarketClient
from predictor import EnsemblePredictor
from telegram_notifier import TelegramNotifier
from trader import TradingBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singletons
predictor = EnsemblePredictor()
polymarket = PolymarketClient(
    api_key=settings.polymarket_api_key,
    api_secret=settings.polymarket_api_secret,
    private_key=settings.polymarket_private_key,
    host=settings.polymarket_host,
)
notifier = TelegramNotifier(
    token=settings.telegram_bot_token,
    chat_id=settings.telegram_chat_id,
)
bot = TradingBot(
    config=settings,
    db_session_factory=SessionLocal,
    predictor=predictor,
    polymarket=polymarket,
    notifier=notifier,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    if bot._running:
        bot.stop()


app = FastAPI(title="PolyTrip Trading Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ────────────────────────────────────────────────

class BotStartRequest(BaseModel):
    strategy: Optional[Literal["tech", "ml", "both"]] = None


class BacktestRequest(BaseModel):
    start_date: str            # ISO date e.g. "2024-01-01"
    end_date: str
    strategy: Literal["tech", "ml", "both"] = "both"
    initial_capital: float = 1000.0


class ConfigUpdateRequest(BaseModel):
    risk_per_trade_usd: Optional[float] = None
    confidence_threshold: Optional[float] = None
    default_strategy: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    polymarket_api_key: Optional[str] = None
    polymarket_api_secret: Optional[str] = None
    polymarket_private_key: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    return bot.get_status()


@app.post("/api/bot/start")
def start_bot(req: BotStartRequest):
    if bot._running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    bot.start(strategy=req.strategy)
    return {"status": "started", "strategy": getattr(bot, "_strategy", settings.default_strategy)}


@app.post("/api/bot/stop")
def stop_bot():
    if not bot._running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    bot.stop()
    return {"status": "stopped"}


@app.post("/api/backtest")
def create_backtest(req: BacktestRequest, background_tasks: BackgroundTasks):
    """Start a backtest run asynchronously."""
    background_tasks.add_task(
        _run_backtest_task,
        req.start_date,
        req.end_date,
        req.strategy,
        req.initial_capital,
    )
    return {"message": "Backtest started. Check /api/backtests for results."}


def _run_backtest_task(start_date, end_date, strategy, initial_capital):
    try:
        run_backtest(
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            initial_capital=initial_capital,
            config=settings,
            db_session_factory=SessionLocal,
            predictor=predictor,
            notifier=notifier,
        )
    except Exception as exc:
        logger.error("Backtest failed: %s", exc, exc_info=True)


@app.get("/api/backtests")
def list_backtests(db: Session = Depends(get_db)):
    runs = db.query(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "start_date": r.start_date,
            "end_date": r.end_date,
            "strategy": r.strategy,
            "initial_capital": r.initial_capital,
            "final_capital": r.final_capital,
            "win_rate": r.win_rate,
            "total_trades": r.total_trades,
            "sharpe_ratio": r.sharpe_ratio,
            "max_drawdown": r.max_drawdown,
            "total_return_pct": r.total_return_pct,
        }
        for r in runs
    ]


@app.get("/api/backtests/{run_id}")
def get_backtest(run_id: int, db: Session = Depends(get_db)):
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return {
        "id": run.id,
        "created_at": run.created_at.isoformat(),
        "start_date": run.start_date,
        "end_date": run.end_date,
        "strategy": run.strategy,
        "initial_capital": run.initial_capital,
        "final_capital": run.final_capital,
        "win_rate": run.win_rate,
        "total_trades": run.total_trades,
        "sharpe_ratio": run.sharpe_ratio,
        "max_drawdown": run.max_drawdown,
        "total_return_pct": run.total_return_pct,
        "equity_curve": json.loads(run.equity_curve_json or "[]"),
        "trades": json.loads(run.trades_json or "[]"),
    }


@app.get("/api/trades")
def list_trades(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    trades = (
        db.query(Trade)
        .order_by(Trade.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(Trade).count()
    return {
        "total": total,
        "trades": [
            {
                "id": t.id,
                "timestamp": t.timestamp.isoformat(),
                "market_id": t.market_id,
                "direction": t.direction,
                "size_usd": t.size_usd,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "strategy": t.strategy,
                "status": t.status,
            }
            for t in trades
        ],
    }


@app.get("/api/config")
def get_config():
    return {
        "risk_per_trade_usd": settings.risk_per_trade_usd,
        "confidence_threshold": settings.confidence_threshold,
        "default_strategy": settings.default_strategy,
        "telegram_configured": bool(settings.telegram_bot_token and settings.telegram_chat_id),
        "polymarket_configured": bool(settings.polymarket_api_key),
        "ml_model_trained": predictor.ml.is_trained(),
    }


@app.put("/api/config")
def update_config(req: ConfigUpdateRequest, db: Session = Depends(get_db)):
    updates = req.model_dump(exclude_none=True)
    for key, value in updates.items():
        existing = db.query(BotConfig).filter(BotConfig.key == key).first()
        if existing:
            existing.value = str(value)
        else:
            db.add(BotConfig(key=key, value=str(value)))
        # Also update in-memory settings
        if hasattr(settings, key):
            setattr(settings, key, value)
    db.commit()
    return {"status": "ok", "updated": list(updates.keys())}


@app.post("/api/predictor/train")
def train_predictor(days: int = 30):
    """Train the ML model on recent BTC data."""
    from datetime import timedelta
    from data_fetcher import fetch_historical_candles

    end = __import__("datetime").datetime.utcnow()
    start = end - timedelta(days=days)
    df = fetch_historical_candles(start=start, end=end)
    if df.empty:
        raise HTTPException(status_code=500, detail="Could not fetch training data")
    metrics = predictor.ml.train(df)
    return {"status": "trained", **metrics}


@app.get("/api/health")
def health():
    return {"status": "ok"}
