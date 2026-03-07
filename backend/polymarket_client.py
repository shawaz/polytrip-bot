"""
Polymarket CLOB client wrapper.

Uses py-clob-client to interact with Polymarket's Central Limit Order Book.
Credentials are read from environment / config.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"


def _current_5min_slug() -> str:
    """
    Compute the slug for the BTC 5-minute market that is open right now.

    Polymarket names each window: btc-updown-5m-{unix_timestamp}
    where the timestamp is the UTC start of the current 5-minute block.

    Example: if it is 14:07 UTC, the active window started at 14:05,
    so the timestamp is for 14:05:00 UTC.
    """
    now = datetime.now(timezone.utc)
    # Round down to the nearest 5-minute boundary
    rounded = now - timedelta(
        minutes=now.minute % 5,
        seconds=now.second,
        microseconds=now.microsecond,
    )
    ts = int(rounded.timestamp())
    return f"btc-updown-5m-{ts}"


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
        """
        Look up the current BTC 5-min market by its exact slug on the Gamma API.
        Returns the condition_id, or None if the market is not open yet.
        """
        slug = _current_5min_slug()
        try:
            resp = requests.get(
                f"{GAMMA_API}/markets",
                params={"slug": slug},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            # Gamma returns a list; grab the first match
            markets = data if isinstance(data, list) else data.get("data", [])
            if not markets:
                logger.warning("No market found for slug %s (not open yet?)", slug)
                return None
            market = markets[0]
            condition_id = market.get("conditionId") or market.get("condition_id")
            logger.info("Found BTC 5-min market: slug=%s condition_id=%s", slug, condition_id)
            return condition_id
        except Exception as exc:
            logger.warning("Could not fetch market for slug %s: %s", slug, exc)
            return None

    def get_token_ids(self, condition_id: str) -> dict:
        """
        Returns the UP (YES) and DOWN (NO) token IDs for a market.
        The Gamma API returns them in clobTokenIds as a JSON-encoded list:
          index 0 = YES/UP, index 1 = NO/DOWN
        """
        try:
            resp = requests.get(
                f"{GAMMA_API}/markets",
                params={"conditionId": condition_id},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            markets = data if isinstance(data, list) else data.get("data", [])
            if not markets:
                return {}
            market = markets[0]
            raw = market.get("clobTokenIds", "[]")
            token_ids = json.loads(raw) if isinstance(raw, str) else raw
            return {
                "yes_token_id": token_ids[0] if len(token_ids) > 0 else None,
                "no_token_id": token_ids[1] if len(token_ids) > 1 else None,
            }
        except Exception as exc:
            logger.warning("Could not fetch token IDs for %s: %s", condition_id, exc)
            return {}

    def get_market_prices(self, condition_id: str) -> dict:
        """
        Return YES and NO prices by fetching the order book for each token.
        Falls back to 0.50 (fair value) if the order book is unavailable.
        """
        try:
            tokens = self.get_token_ids(condition_id)
            client = self._get_client()
            yes_price = 0.5
            no_price = 0.5
            if tokens.get("yes_token_id"):
                book = client.get_order_book(tokens["yes_token_id"])
                yes_price = float(book.get("best_ask", 0.5))
                no_price = round(1.0 - yes_price, 4)
            return {"yes_price": yes_price, "no_price": no_price, **tokens}
        except Exception as exc:
            logger.warning("Could not get market prices for %s: %s", condition_id, exc)
            return {"yes_price": 0.5, "no_price": 0.5}

    def place_order(
        self, condition_id: str, side: str, size_usd: float
    ) -> Optional[str]:
        """
        Place a FOK market order using the correct outcome token ID.
        side: 'YES' (UP) or 'NO' (DOWN)
        Returns order_id or None on failure.
        """
        try:
            from py_clob_client.clob_types import MarketOrderArgs

            client = self._get_client()
            prices = self.get_market_prices(condition_id)

            # Use the specific outcome token, not the condition_id
            token_id = prices.get("yes_token_id") if side == "YES" else prices.get("no_token_id")
            if not token_id:
                logger.error("No token ID found for side=%s on %s", side, condition_id)
                return None

            price = prices["yes_price"] if side == "YES" else prices["no_price"]
            size = size_usd / price if price > 0 else size_usd

            args = MarketOrderArgs(token_id=token_id, amount=size)
            resp = client.create_market_order(args)
            order_id = resp.get("orderID") or resp.get("id")
            logger.info("Placed %s order %s (token=%s)", side, order_id, token_id)
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
