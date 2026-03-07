"""Send Telegram notifications for trades and backtest results."""

import logging
import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self._base = f"https://api.telegram.org/bot{token}"

    def _send(self, text: str) -> bool:
        if not self.token or not self.chat_id:
            logger.debug("Telegram not configured, skipping notification")
            return False
        try:
            resp = requests.post(
                f"{self._base}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Telegram send failed: %s", exc)
            return False

    def notify_trade_opened(self, trade) -> bool:
        text = (
            f"🟢 <b>TRADE OPENED</b>\n"
            f"BTC 5m <b>{trade.direction}</b>\n"
            f"Entry price: <b>${trade.entry_price:.4f}</b>\n"
            f"Size: <b>${trade.size_usd:.2f}</b>\n"
            f"Strategy: <b>{trade.strategy}</b>\n"
            f"Order ID: <code>{trade.polymarket_order_id}</code>"
        )
        return self._send(text)

    def notify_trade_closed(self, trade) -> bool:
        pnl = trade.pnl or 0.0
        pct = (pnl / trade.size_usd * 100) if trade.size_usd else 0.0
        result_emoji = "✅ Win" if pnl > 0 else "❌ Loss"
        text = (
            f"🔴 <b>TRADE CLOSED</b>\n"
            f"BTC 5m {trade.direction}\n"
            f"Entry: <b>${trade.entry_price:.4f}</b> → Exit: <b>${trade.exit_price:.4f}</b>\n"
            f"P&amp;L: <b>${pnl:+.2f} ({pct:+.1f}%)</b>\n"
            f"{result_emoji}"
        )
        return self._send(text)

    def notify_backtest_complete(self, run) -> bool:
        ret = run.total_return_pct or 0.0
        wr = run.win_rate or 0.0
        sharpe = run.sharpe_ratio or 0.0
        dd = run.max_drawdown or 0.0
        text = (
            f"📊 <b>BACKTEST COMPLETE</b>\n"
            f"Period: <b>{run.start_date} → {run.end_date}</b>\n"
            f"Strategy: <b>{run.strategy}</b>\n"
            f"Capital: ${run.initial_capital:.0f} → <b>${run.final_capital:.2f}</b>\n"
            f"Win Rate: <b>{wr:.1f}%</b> ({run.total_trades} trades)\n"
            f"Return: <b>{ret:+.1f}%</b>\n"
            f"Sharpe: <b>{sharpe:.2f}</b>\n"
            f"Max Drawdown: <b>{dd:.1f}%</b>"
        )
        return self._send(text)
