"""
Historical backtesting engine.

Downloads BTC 1-min candles from Binance, simulates 5-min prediction trades,
and computes performance metrics.
"""

import json
import logging
import math
from datetime import datetime
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _sharpe(returns: list, risk_free: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    std = arr.std()
    if std == 0:
        return 0.0
    return float((arr.mean() - risk_free) / std * math.sqrt(252 * 288))  # 288 5-min bars/day


def _max_drawdown(equity: list) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak else 0.0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def run_backtest(
    start_date: str,
    end_date: str,
    strategy: Literal["tech", "ml", "both"],
    initial_capital: float,
    config,
    db_session_factory,
    predictor,
    notifier,
) -> dict:
    """
    Run backtest and persist a BacktestRun record. Returns the run dict.
    """
    from data_fetcher import fetch_historical_candles
    from models import BacktestRun

    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    logger.info("Fetching candles %s → %s", start_date, end_date)
    df = fetch_historical_candles(start=start_dt, end=end_dt)

    if df.empty:
        raise ValueError("No candle data returned for the requested date range.")

    capital = initial_capital
    equity_curve = []
    trade_results = []
    returns = []

    # Step through in 5-min windows (5 candles)
    step = 5
    rows = df.reset_index()
    n = len(rows)

    for i in range(50, n - step, step):  # need 50 rows for indicators
        window = rows.iloc[max(0, i - 50): i].copy()
        if len(window) < 20:
            continue

        window = window.rename(columns={"open_time": "open_time"})
        window = window.set_index("open_time") if "open_time" in window.columns else window

        try:
            direction, confidence = predictor.predict(window, strategy=strategy)
        except Exception:
            continue

        if confidence < config.confidence_threshold:
            equity_curve.append({"date": str(rows.iloc[i]["open_time"]), "value": round(capital, 2)})
            continue

        entry_price = float(rows.iloc[i]["close"])
        exit_price = float(rows.iloc[min(i + step, n - 1)]["close"])

        went_up = exit_price > entry_price
        won = (direction == "YES" and went_up) or (direction == "NO" and not went_up)

        risk = config.risk_per_trade_usd
        # Binary-style payout: assume entry at 0.5, payout 1.0 or 0.0
        pnl = risk * (1.0 if won else -1.0)
        capital += pnl

        ret = pnl / risk
        returns.append(ret)

        trade_results.append({
            "date": str(rows.iloc[i]["open_time"]),
            "direction": direction,
            "confidence": confidence,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "won": won,
        })

        equity_curve.append({"date": str(rows.iloc[i]["open_time"]), "value": round(capital, 2)})

    total_trades = len(trade_results)
    wins = sum(1 for t in trade_results if t["won"])
    win_rate = wins / total_trades * 100 if total_trades else 0.0
    total_return_pct = (capital - initial_capital) / initial_capital * 100
    sharpe = _sharpe(returns)
    max_dd = _max_drawdown([e["value"] for e in equity_curve])

    db = db_session_factory()
    try:
        run = BacktestRun(
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            initial_capital=initial_capital,
            final_capital=round(capital, 2),
            win_rate=round(win_rate, 2),
            total_trades=total_trades,
            sharpe_ratio=round(sharpe, 3),
            max_drawdown=max_dd,
            total_return_pct=round(total_return_pct, 2),
            equity_curve_json=json.dumps(equity_curve),
            trades_json=json.dumps(trade_results),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

        notifier.notify_backtest_complete(run)

        return {
            "id": run_id,
            "start_date": start_date,
            "end_date": end_date,
            "strategy": strategy,
            "initial_capital": initial_capital,
            "final_capital": round(capital, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_trades,
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown": max_dd,
            "total_return_pct": round(total_return_pct, 2),
            "equity_curve": equity_curve,
            "trades": trade_results,
        }
    finally:
        db.close()
