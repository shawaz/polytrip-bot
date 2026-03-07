import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

BINANCE_BASE = "https://api.binance.com"


def fetch_candles(
    symbol: str = "BTCUSDT",
    interval: str = "1m",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 1000,
) -> pd.DataFrame:
    """Fetch OHLCV candles from Binance (no auth required)."""
    params: dict = {"symbol": symbol, "interval": interval, "limit": limit}
    if start:
        params["startTime"] = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
    if end:
        params["endTime"] = int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)

    resp = requests.get(f"{BINANCE_BASE}/api/v3/klines", params=params, timeout=10)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df.set_index("open_time")


def fetch_historical_candles(
    symbol: str = "BTCUSDT",
    interval: str = "1m",
    start: datetime = None,
    end: datetime = None,
) -> pd.DataFrame:
    """Fetch all candles between start and end, handling Binance 1000-row pagination."""
    frames = []
    current_start = start
    while current_start < end:
        df = fetch_candles(symbol, interval, start=current_start, end=end, limit=1000)
        if df.empty:
            break
        frames.append(df)
        last_time = df.index[-1].to_pydatetime().replace(tzinfo=None)
        if last_time >= end or len(df) < 1000:
            break
        current_start = last_time
        time.sleep(0.1)  # respect rate limits
    return pd.concat(frames).drop_duplicates() if frames else pd.DataFrame()


def fetch_latest_candles(n: int = 60, symbol: str = "BTCUSDT") -> pd.DataFrame:
    """Fetch the most recent N 1-min candles."""
    return fetch_candles(symbol, interval="1m", limit=n)
