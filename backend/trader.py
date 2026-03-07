"""
Live trading loop.

Uses APScheduler to run a cycle every 5 minutes:
  1. Fetch latest BTC candles
  2. Get prediction
  3. If confident enough and no open position: place order
  4. If open position: check resolution and close
"""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self, config, db_session_factory, predictor, polymarket, notifier):
        self.config = config
        self.db_session_factory = db_session_factory
        self.predictor = predictor
        self.polymarket = polymarket
        self.notifier = notifier

        self._scheduler = BackgroundScheduler()
        self._running = False
        self._open_trade_id: Optional[int] = None
        self._market_id: Optional[str] = None
        self._last_error: Optional[str] = None

    def start(self, strategy: Optional[str] = None):
        if self._running:
            return
        self._strategy = strategy or self.config.default_strategy
        # Market ID is looked up fresh each cycle — do not cache it here,
        # because each 5-minute window has a different market.

        self._scheduler.add_job(
            self.run_cycle,
            CronTrigger(minute="*/5"),  # fires at :00, :05, :10, ... (UTC clock boundaries)
            id="trading_cycle",
            max_instances=1,            # never overlap if a cycle runs long
        )
        self._scheduler.start()
        self._running = True
        logger.info("Trading bot started (strategy=%s)", self._strategy)

    def stop(self):
        if not self._running:
            return
        self._scheduler.remove_all_jobs()
        self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("Trading bot stopped")

    def get_status(self) -> dict:
        from sqlalchemy import func
        from models import Trade

        db = self.db_session_factory()
        try:
            open_trade = (
                db.query(Trade).filter(Trade.status == "open").first()
                if self._running else None
            )
            today = datetime.utcnow().date()
            today_pnl = (
                db.query(func.sum(Trade.pnl))
                .filter(
                    Trade.status == "closed",
                    func.date(Trade.timestamp) == today,
                )
                .scalar()
                or 0.0
            )
            total_pnl = (
                db.query(func.sum(Trade.pnl)).filter(Trade.status == "closed").scalar() or 0.0
            )
            total_trades = db.query(Trade).filter(Trade.status == "closed").count()
            wins = (
                db.query(Trade)
                .filter(Trade.status == "closed", Trade.pnl > 0)
                .count()
            )
            win_rate = (wins / total_trades * 100) if total_trades else 0.0
        finally:
            db.close()

        return {
            "running": self._running,
            "paper_trading": self.config.paper_trading,
            "strategy": getattr(self, "_strategy", self.config.default_strategy),
            "market_id": self._market_id,
            "open_trade": self._trade_to_dict(open_trade),
            "today_pnl": round(today_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 1),
            "last_error": self._last_error,
        }

    def _trade_to_dict(self, trade) -> Optional[dict]:
        if trade is None:
            return None
        return {
            "id": trade.id,
            "direction": trade.direction,
            "size_usd": trade.size_usd,
            "entry_price": trade.entry_price,
            "strategy": trade.strategy,
            "timestamp": trade.timestamp.isoformat(),
        }

    def run_cycle(self):
        """Main trading cycle — called every 5 minutes at clock boundaries."""
        try:
            from data_fetcher import fetch_latest_candles
            from models import Trade

            df = fetch_latest_candles(n=60)
            if df.empty:
                logger.warning("No candle data available")
                return

            direction, confidence = self.predictor.predict(df, strategy=self._strategy)
            logger.info("Prediction: %s (confidence=%.3f)", direction, confidence)

            # Resolve the market for THIS window (changes every 5 minutes)
            if self.config.paper_trading:
                self._market_id = None  # force paper path — no real orders placed
            else:
                self._market_id = self.polymarket.find_btc_5min_market()
                if not self._market_id:
                    logger.warning("No BTC 5-min market open yet — skipping cycle")

            db = self.db_session_factory()
            try:
                open_trade = db.query(Trade).filter(Trade.status == "open").first()

                if open_trade:
                    self._try_close_trade(open_trade, db)
                elif confidence >= self.config.confidence_threshold:
                    self._open_trade(direction, confidence, db)
            finally:
                db.close()

            self._last_error = None
        except Exception as exc:
            self._last_error = str(exc)
            logger.error("Trading cycle error: %s", exc, exc_info=True)

    def _open_trade(self, direction: str, confidence: float, db):
        from models import Trade

        prices = {}
        order_id = None
        if self._market_id:
            prices = self.polymarket.get_market_prices(self._market_id)
            order_id = self.polymarket.place_order(
                self._market_id, direction, self.config.risk_per_trade_usd
            )

        entry_price = prices.get("yes_price" if direction == "YES" else "no_price", 0.5)
        trade = Trade(
            market_id=self._market_id or "paper",
            direction=direction,
            size_usd=self.config.risk_per_trade_usd,
            entry_price=entry_price,
            strategy=self._strategy,
            status="open",
            polymarket_order_id=order_id,
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)

        self.notifier.notify_trade_opened(trade)
        logger.info("Opened trade %d: %s @ %.4f", trade.id, direction, entry_price)

    def _try_close_trade(self, trade, db):
        if not trade.polymarket_order_id and trade.market_id == "paper":
            # Paper trade: simulate close after one cycle
            from data_fetcher import fetch_latest_candles
            df = fetch_latest_candles(n=5)
            if df.empty:
                return
            current_price = float(df["close"].iloc[-1])
            # Simulate Polymarket-style binary payout
            # If direction=YES and price went up → payout ≈ 1.0, else ≈ 0.0
            prev_price = float(df["close"].iloc[0])
            went_up = current_price > prev_price
            won = (trade.direction == "YES" and went_up) or (trade.direction == "NO" and not went_up)
            payout = trade.size_usd * (1.0 / trade.entry_price if won else 0.0)
            pnl = payout - trade.size_usd

            trade.exit_price = current_price
            trade.pnl = round(pnl, 2)
            trade.status = "closed"
            db.commit()
            db.refresh(trade)
            self.notifier.notify_trade_closed(trade)
            return

        if trade.polymarket_order_id:
            order = self.polymarket.get_order(trade.polymarket_order_id)
            status = order.get("status", "")
            if status in ("MATCHED", "FILLED"):
                fill_price = float(order.get("avg_price", trade.entry_price))
                pnl = (fill_price - trade.entry_price) * trade.size_usd
                trade.exit_price = fill_price
                trade.pnl = round(pnl, 2)
                trade.status = "closed"
                db.commit()
                db.refresh(trade)
                self.notifier.notify_trade_closed(trade)
