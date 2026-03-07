from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    market_id = Column(String, nullable=False)
    direction = Column(String, nullable=False)        # YES | NO
    size_usd = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    strategy = Column(String, nullable=False)         # tech | ml | both
    status = Column(String, default="open")           # open | closed | cancelled
    polymarket_order_id = Column(String, nullable=True)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    strategy = Column(String, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    equity_curve_json = Column(Text, nullable=True)   # JSON list of {date, value}
    trades_json = Column(Text, nullable=True)          # JSON list of per-trade results


class BotConfig(Base):
    __tablename__ = "bot_config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
