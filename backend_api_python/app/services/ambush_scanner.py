"""
Ambush Scanner V1 - 埋伏信号扫描器
====================================
QD-native pre-positioning signal detector.
Detects accumulation/distribution patterns for early entry.

Logic:
1. Monitor OI + price divergence
2. Detect bottom accumulation (OI rising, price flat/falling)
3. Detect top distribution (OI falling, price flat/rising)
4. Output ambush signals with confidence levels
"""
from __future__ import annotations

import os
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

AMBUSH_OI_LOOKBACK = int(os.getenv("AMBUSH_OI_LOOKBACK", "30"))
AMBUSH_PRICE_FLAT_THRESHOLD = float(os.getenv("AMBUSH_FLAT_THRESHOLD", "0.005"))


@dataclass
class AmbushSignal:
    """A pre-positioning ambush signal."""
    symbol: str
    pattern: str       # bottom_accumulation / top_distribution / coil_compression
    direction: str     # LONG / SHORT
    confidence: str    # high / mid / low
    price: float
    oi_change_pct: float = 0.0
    duration_minutes: int = 0
    score: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "pattern": self.pattern,
            "direction": self.direction,
            "confidence": self.confidence,
            "price": self.price,
            "oi_change_pct": round(self.oi_change_pct, 2),
            "duration_minutes": self.duration_minutes,
            "score": self.score,
            "timestamp": self.timestamp,
        }


class AmbushScanner:
    """埋伏信号扫描器 - detects accumulation/distribution."""

    def __init__(self):
        self._signals: List[AmbushSignal] = []
        self._max_signals = 100

    def _get_client(self):
        try:
            from app.services.live_trading.factory import create_client
            from app.services.live_trading.contracts import normalize_order_market_type
            return create_client(
                exchange_id="binance",
                market_type=normalize_order_market_type("swap"),
            )
        except Exception:
            return None

    def scan_symbol(self, symbol: str) -> Optional[AmbushSignal]:
        """Scan for ambush patterns on a symbol."""
        client = self._get_client()
        if not client:
            return None

        try:
            oi_pct = 0.0
            price_change = 0.0
            price = 0.0

            # Get OI data
            if hasattr(client, "get_open_interest"):
                oi_data = client.get_open_interest(symbol=symbol)
                if oi_data:
                    oi_pct = float(oi_data.get("percentage", 0))

            # Get price data
            if hasattr(client, "get_ticker"):
                ticker = client.get_ticker(symbol=symbol)
                if ticker:
                    price = float(ticker.get("lastPrice", 0))
                    price_change = float(ticker.get("priceChangePercent", 0))

            if price <= 0:
                return None

            # Pattern detection
            pattern = None
            direction = "NEUTRAL"
            confidence = "low"
            score = 0

            # Bottom accumulation: OI rising + price flat or slightly falling
            if oi_pct > 3 and abs(price_change) < AMBUSH_PRICE_FLAT_THRESHOLD * 100:
                pattern = "bottom_accumulation"
                direction = "LONG"
                confidence = "high" if oi_pct > 8 else "mid"
                score = 8 if oi_pct > 8 else 5

            # Top distribution: OI falling + price flat or slightly rising
            elif oi_pct < -3 and abs(price_change) < AMBUSH_PRICE_FLAT_THRESHOLD * 100:
                pattern = "top_distribution"
                direction = "SHORT"
                confidence = "high" if oi_pct < -8 else "mid"
                score = 8 if oi_pct < -8 else 5

            # Coil compression: OI flat + price very flat
            elif abs(oi_pct) < 2 and abs(price_change) < 1.0:
                pattern = "coil_compression"
                direction = "NEUTRAL"
                confidence = "low"
                score = 3

            if pattern is None:
                return None

            signal = AmbushSignal(
                symbol=symbol,
                pattern=pattern,
                direction=direction,
                confidence=confidence,
                price=price,
                oi_change_pct=oi_pct,
                score=score,
                timestamp=datetime.now(BJT).isoformat(),
            )

            self._signals.append(signal)
            if len(self._signals) > self._max_signals:
                self._signals = self._signals[-self._max_signals:]

            return signal

        except Exception as e:
            logger.debug(f"Ambush scan failed for {symbol}: {e}")
            return None

    def scan_watchlist(self, symbols: List[str]) -> List[AmbushSignal]:
        """Scan a watchlist for ambush patterns."""
        results = []
        for sym in symbols:
            result = self.scan_symbol(sym)
            if result:
                results.append(result)
        return results

    def get_recent(self, n: int = 10) -> List[dict]:
        return [s.to_dict() for s in self._signals[-n:]]

    def get_status(self) -> dict:
        return {
            "recent_signals": len(self._signals),
            "last_5": self.get_recent(5),
        }


_ambush: Optional[AmbushScanner] = None


def get_ambush_scanner() -> AmbushScanner:
    global _ambush
    if _ambush is None:
        _ambush = AmbushScanner()
    return _ambush
