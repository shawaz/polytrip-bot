"""
BTC 5-min direction predictor.

Two strategies:
  - TechIndicatorPredictor: rule-based RSI / MACD / Bollinger Bands scoring
  - MLPredictor: GradientBoostingClassifier trained on indicator features
  - EnsemblePredictor: averages both confidence scores
"""

import os
from typing import Literal, Tuple

import joblib
import numpy as np
import pandas as pd
import ta

MODEL_PATH = os.environ.get("MODEL_PATH", "ml_model.pkl")


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicator columns to a candle DataFrame."""
    df = df.copy()
    close = df["close"]

    # RSI
    df["rsi"] = ta.momentum.RSIIndicator(close, window=14).rsi()

    # MACD
    macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    df["bb_pct"] = bb.bollinger_pband()  # 0=low, 1=high

    # EMAs
    df["ema5"] = ta.trend.EMAIndicator(close, window=5).ema_indicator()
    df["ema10"] = ta.trend.EMAIndicator(close, window=10).ema_indicator()
    df["ema20"] = ta.trend.EMAIndicator(close, window=20).ema_indicator()

    # Momentum
    df["momentum5"] = close.pct_change(5)
    df["momentum10"] = close.pct_change(10)

    # Volume change
    df["volume_change"] = df["volume"].pct_change(5)

    return df


FEATURE_COLS = [
    "rsi", "macd", "macd_signal", "macd_diff",
    "bb_pct", "ema5", "ema10", "ema20",
    "momentum5", "momentum10", "volume_change",
]


class TechIndicatorPredictor:
    """Rule-based predictor using RSI, MACD, and Bollinger Bands."""

    def predict(self, df: pd.DataFrame) -> Tuple[Literal["YES", "NO"], float]:
        df = compute_features(df)
        row = df.dropna().iloc[-1]

        score = 0.0  # positive = bullish, negative = bearish

        # RSI signal
        if row["rsi"] < 35:
            score += 1.5
        elif row["rsi"] < 45:
            score += 0.5
        elif row["rsi"] > 65:
            score -= 1.5
        elif row["rsi"] > 55:
            score -= 0.5

        # MACD signal
        if row["macd_diff"] > 0:
            score += 1.0
        else:
            score -= 1.0

        # Bollinger Bands signal
        if row["bb_pct"] < 0.2:
            score += 1.0  # near lower band → potential bounce
        elif row["bb_pct"] > 0.8:
            score -= 1.0  # near upper band → potential reversal

        # EMA trend
        if row["ema5"] > row["ema20"]:
            score += 0.5
        else:
            score -= 0.5

        # Clamp score to [-4, 4] and map to [0.5, 0.85] confidence
        score = max(-4.0, min(4.0, score))
        confidence = 0.5 + abs(score) / 4.0 * 0.35

        direction: Literal["YES", "NO"] = "YES" if score > 0 else "NO"
        return direction, round(confidence, 3)


class MLPredictor:
    """GradientBoostingClassifier predictor trained on indicator features."""

    def __init__(self):
        self._model = None
        self._load()

    def _load(self):
        if os.path.exists(MODEL_PATH):
            self._model = joblib.load(MODEL_PATH)

    def is_trained(self) -> bool:
        return self._model is not None

    def train(self, df: pd.DataFrame) -> dict:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score

        df = compute_features(df).dropna()

        # Label: 1 if close price 5 rows later is higher
        df["label"] = (df["close"].shift(-5) > df["close"]).astype(int)
        df = df.dropna()

        X = df[FEATURE_COLS].values
        y = df["label"].values

        model = GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42
        )
        scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
        model.fit(X, y)

        self._model = model
        joblib.dump(model, MODEL_PATH)

        return {
            "cv_accuracy_mean": round(float(scores.mean()), 4),
            "cv_accuracy_std": round(float(scores.std()), 4),
            "training_samples": len(X),
        }

    def predict(self, df: pd.DataFrame) -> Tuple[Literal["YES", "NO"], float]:
        if not self.is_trained():
            raise RuntimeError("ML model not trained. Call /api/predictor/train first.")

        df = compute_features(df).dropna()
        row = df[FEATURE_COLS].iloc[[-1]].values
        proba = self._model.predict_proba(row)[0]  # [prob_down, prob_up]
        prob_up = proba[1]

        direction: Literal["YES", "NO"] = "YES" if prob_up >= 0.5 else "NO"
        confidence = prob_up if prob_up >= 0.5 else 1.0 - prob_up
        return direction, round(confidence, 3)


class EnsemblePredictor:
    """Averages tech and ML signals."""

    def __init__(self):
        self.tech = TechIndicatorPredictor()
        self.ml = MLPredictor()

    def predict(
        self, df: pd.DataFrame, strategy: str = "both"
    ) -> Tuple[Literal["YES", "NO"], float]:
        if strategy == "tech":
            return self.tech.predict(df)
        if strategy == "ml":
            return self.ml.predict(df)

        # both: average YES probability
        tech_dir, tech_conf = self.tech.predict(df)
        tech_prob_yes = tech_conf if tech_dir == "YES" else 1.0 - tech_conf

        if self.ml.is_trained():
            ml_dir, ml_conf = self.ml.predict(df)
            ml_prob_yes = ml_conf if ml_dir == "YES" else 1.0 - ml_conf
            avg_prob_yes = (tech_prob_yes + ml_prob_yes) / 2
        else:
            avg_prob_yes = tech_prob_yes

        direction: Literal["YES", "NO"] = "YES" if avg_prob_yes >= 0.5 else "NO"
        confidence = avg_prob_yes if avg_prob_yes >= 0.5 else 1.0 - avg_prob_yes
        return direction, round(confidence, 3)
