"""
Lightning Scanner V1 - 闪电信号扫描器
=======================================
QD-native volume-tape burst signal detector.
Detects sudden volume spikes with directional tape bias.

Logic:
1. Monitor real-time taker volume bursts
2. Detect volume spike (>Nx average)
3. Classify tape direction (bullish/bearish)
4. Output quick signals
"""
from __future__ import annotations

import os
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import deque

from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

# ============================================================
# Configuration
# ============================================================

LIGHTNING_VOL_THRESHOLD = float(os.getenv("LIGHTNING_VOL_THRESHOLD", "3.0"))    # Nx average vol
LIGHTNING_MIN_VOL_USD = float(os.getenv("LIGHTNING_MIN_VOL", "100000"))          # $100k min burst
LIGHTNING_LOOKBACK_BARS = int(os.getenv("LIGHTNING_LOOKBACK", "20"))             # bars for avg calc
LIGHTNING_COOLDOWN = int(os.getenv("LIGHTNING_COOLDOWN", "120"))                 # seconds cooldown per coin


@dataclass
class LightningSignal:
    """A lightning-fast volume burst signal."""
    symbol: str
    direction: str      # LONG / SHORT
    price: float
    vol_ratio: float    # current vol / avg vol
    tape: str           # bullish / bearish / neutral
    timestamp: str
    score: int = 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "price": self.price,
            "vol_ratio": round(self.vol_ratio, 1),
            "tape": self.tape,
            "score": self.score,
            "timestamp": self.timestamp,
        }


class LightningScanner:
    """闪电信号扫描器 - detects sudden volume bursts."""

    def __init__(self):
        self._vol_history: Dict[str, deque] = {}
        self._cooldowns: Dict[str, float] = {}
        self._signals: List[LightningSignal] = []
        self._max_signals = 200

    def _get_exchange_client(self):
        """Get Binance futures client."""
        try:
            from app.services.live_trading.factory import create_client
            from app.services.live_trading.contracts import normalize_order_market_type
            return create_client(
                exchange_id="binance",
                market_type=normalize_order_market_type("swap"),
            )
        except Exception:
            return None

    def scan_symbol(self, symbol: str) -> Optional[LightningSignal]:
        """Scan a single symbol for lightning signal."""
        if symbol in self._cooldowns:
            if time.time() - self._cooldowns[symbol] < LIGHTNING_COOLDOWN:
                return None
            del self._cooldowns[symbol]

        client = self._get_exchange_client()
        if not client:
            return None

        try:
            # Get recent taker volume
            if hasattr(client, "get_taker_volume"):
                taker_data = client.get_taker_volume(symbol=symbol, limit=LIGHTNING_LOOKBACK_BARS + 5)
            else:
                return None

            if not taker_data or len(taker_data) < 3:
                return None

            # Calculate volume metrics
            recent = taker_data[:5]
            historical = taker_data[5:] if len(taker_data) > 5 else taker_data[1:]

            recent_total = sum(
                float(d.get("buyVolume", 0)) + float(d.get("sellVolume", 0))
                for d in recent
            )
            hist_total = sum(
                float(d.get("buyVolume", 0)) + float(d.get("sellVolume", 0))
                for d in historical
            )

            avg_hist = hist_total / max(len(historical), 1)
            if avg_hist <= 0:
                return None

            vol_ratio = recent_total / avg_hist

            if vol_ratio < LIGHTNING_VOL_THRESHOLD or recent_total < LIGHTNING_MIN_VOL_USD:
                return None

            # Determine tape direction
            buy_vol = sum(float(d.get("buyVolume", 0)) for d in recent)
            sell_vol = sum(float(d.get("sellVolume", 0)) for d in recent)
            buy_ratio = buy_vol / max(buy_vol + sell_vol, 1)

            if buy_ratio > 0.55:
                tape = "bullish"
                direction = "LONG"
                score = min(int(vol_ratio * 2), 10)
            elif buy_ratio < 0.45:
                tape = "bearish"
                direction = "SHORT"
                score = min(int(vol_ratio * 2), 10)
            else:
                tape = "neutral"
                direction = "NEUTRAL"
                score = 0

            # Get current price
            price = 0.0
            try:
                ticker = client.get_ticker(symbol=symbol) if hasattr(client, "get_ticker") else {}
                price = float(ticker.get("lastPrice", 0))
            except Exception:
                pass

            signal = LightningSignal(
                symbol=symbol,
                direction=direction,
                price=price,
                vol_ratio=round(vol_ratio, 1),
                tape=tape,
                timestamp=datetime.now(BJT).isoformat(),
                score=score,
            )

            self._signals.append(signal)
            if len(self._signals) > self._max_signals:
                self._signals = self._signals[-self._max_signals:]
            self._cooldowns[symbol] = time.time()

            return signal

        except Exception as e:
            logger.debug(f"Lightning scan failed for {symbol}: {e}")
            return None

    def scan_watchlist(self, symbols: List[str]) -> List[LightningSignal]:
        """Scan a watchlist of symbols."""
        results = []
        for sym in symbols:
            result = self.scan_symbol(sym)
            if result and result.direction != "NEUTRAL":
                results.append(result)
        return results

    def get_recent(self, n: int = 10) -> List[dict]:
        """Get recent signals."""
        return [s.to_dict() for s in self._signals[-n:]]

    def get_status(self) -> dict:
        return {
            "recent_signals": len(self._signals),
            "cooldowns": len(self._cooldowns),
            "last_5": self.get_recent(5),
        }


# ============================================================
# Singleton
# ============================================================

_lightning: Optional[LightningScanner] = None


def get_lightning_scanner() -> LightningScanner:
    global _lightning
    if _lightning is None:
        _lightning = LightningScanner()
    return _lightning
