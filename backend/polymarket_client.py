"""
Polymarket CLOB client wrapper.

Uses py-clob-client to interact with Polymarket's Central Limit Order Book.
Credentials are read from environment / config.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Market slug pattern we look for (Polymarket-specific)
BTC_5MIN_SLUG_KEYWORDS = ["bitcoin", "btc", "5", "minute", "min"]


class PolymarketClient:
    def __init__(self, api_key: str, api_secret: str, private_key: str, host: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.private_key = private_key
        self.host = host
        self._client = None

    def _get_client(self):
        if self._client is None:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds

            creds = ApiCreds(
                api_key=self.api_key,
                api_secret=self.api_secret,
                api_passphrase="",
            )
            self._client = ClobClient(self.host, key=self.private_key, creds=creds)
        return self._client

    def find_btc_5min_market(self) -> Optional[str]:
        """Search Polymarket for an active BTC 5-min up/down market. Returns condition_id."""
        try:
            client = self._get_client()
            markets = client.get_markets()
            for m in markets.get("data", []):
                question = (m.get("question") or "").lower()
                slug = (m.get("market_slug") or "").lower()
                if any(k in question or k in slug for k in ["btc", "bitcoin"]):
                    if any(k in question or k in slug for k in ["5 min", "5min", "5-min"]):
                        logger.info("Found BTC 5-min market: %s", m.get("condition_id"))
                        return m["condition_id"]
        except Exception as exc:
            logger.warning("Could not find BTC 5-min market: %s", exc)
        return None

    def get_market_prices(self, condition_id: str) -> dict:
        """Return YES and NO token prices for a market."""
        try:
            client = self._get_client()
            book = client.get_order_book(condition_id)
            yes_price = float(book.get("best_ask", 0.5))
            no_price = round(1.0 - yes_price, 4)
            return {"yes_price": yes_price, "no_price": no_price}
        except Exception as exc:
            logger.warning("Could not get market prices: %s", exc)
            return {"yes_price": 0.5, "no_price": 0.5}

    def place_order(
        self, condition_id: str, side: str, size_usd: float
    ) -> Optional[str]:
        """
        Place a market order.
        side: 'YES' or 'NO'
        Returns order_id or None on failure.
        """
        try:
            from py_clob_client.clob_types import MarketOrderArgs, BUY

            client = self._get_client()
            prices = self.get_market_prices(condition_id)
            price = prices["yes_price"] if side == "YES" else prices["no_price"]
            size = size_usd / price if price > 0 else size_usd

            args = MarketOrderArgs(token_id=condition_id, amount=size)
            resp = client.create_market_order(args)
            order_id = resp.get("orderID") or resp.get("id")
            logger.info("Placed %s order %s on %s", side, order_id, condition_id)
            return order_id
        except Exception as exc:
            logger.error("Failed to place order: %s", exc)
            return None

    def get_order(self, order_id: str) -> dict:
        """Get order status."""
        try:
            client = self._get_client()
            return client.get_order(order_id)
        except Exception as exc:
            logger.warning("Could not get order %s: %s", order_id, exc)
            return {}

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            client = self._get_client()
            client.cancel(order_id)
            return True
        except Exception as exc:
            logger.warning("Could not cancel order %s: %s", order_id, exc)
            return False
