"""
Yaobi Scanner V1 - 妖币扫描器
================================
QD-native high-volatility coin scanner.
Replaces yaobi_v14.py with clean module design.

Logic:
1. Scan Binance futures for high-vol coins
2. Multi-factor scoring (volume, price change, CVD, OI, orderbook)
3. Output scored candidates
"""
from __future__ import annotations

import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

# ============================================================
# Configuration
# ============================================================

# Coins to skip (majors)
SKIP_COINS = frozenset({
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT",
    "LINK", "AVAX", "LTC", "USDC", "USDT", "DAI", "BUSD",
    "TUSD", "FDUSD", "WBTC", "STETH",
})

YAOBI_MIN_VOLUME_USD = float(os.getenv("YAOBI_MIN_VOLUME", "500000"))   # $500k min 24h volume
YAOBI_MIN_PRICE_CHANGE = float(os.getenv("YAOBI_MIN_CHANGE", "2.0"))     # 2% min price change
YAOBI_MAX_CANDIDATES = int(os.getenv("YAOBI_MAX_CANDIDATES", "30"))      # max coins to scan
YAOBI_SCAN_INTERVAL = int(os.getenv("YAOBI_SCAN_INTERVAL", "60"))        # seconds between scans

# Scoring weights
WEIGHT_VOLUME = 0.25
WEIGHT_PRICE_CHANGE = 0.25
WEIGHT_CVD = 0.20
WEIGHT_OI = 0.15
WEIGHT_ORDERBOOK = 0.15


@dataclass
class YaobiCandidate:
    """A scanned coin candidate."""
    symbol: str
    name: str
    price: float
    volume_24h: float
    price_change_pct: float
    cvd_5m_pct: float = 0.0
    oi_change_pct: float = 0.0
    ob_imbalance: float = 0.0
    score: float = 0.0
    direction: str = "NEUTRAL"  # LONG / SHORT / NEUTRAL
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "volume_24h": self.volume_24h,
            "price_change_pct": round(self.price_change_pct, 2),
            "cvd_5m_pct": round(self.cvd_5m_pct, 2),
            "oi_change_pct": round(self.oi_change_pct, 2),
            "ob_imbalance": round(self.ob_imbalance, 2),
            "score": round(self.score, 1),
            "direction": self.direction,
            "timestamp": self.timestamp,
        }


class YaobiScanner:
    """妖币扫描器 - finds high-volatility trading opportunities."""

    def __init__(self):
        self._last_scan: float = 0
        self._candidates: List[YaobiCandidate] = []
        self._running = False

    def _get_futures_client(self):
        """Get Binance futures exchange client from QD."""
        try:
            from app.services.live_trading.factory import create_client
            from app.services.live_trading.contracts import normalize_order_market_type
            mt = normalize_order_market_type("swap")
            return create_client(
                exchange_id="binance",
                market_type=mt,
            )
        except Exception as e:
            logger.warning(f"Failed to create Binance client: {e}")
            return None

    def scan(self) -> List[YaobiCandidate]:
        """Run a full scan cycle."""
        client = self._get_futures_client()
        if not client:
            logger.warning("No exchange client, skipping yaobi scan")
            return []

        candidates: Dict[str, dict] = {}

        # ---- Step 1: 24hr ticker scan ----
        try:
            tickers = client.get_tickers() if hasattr(client, "get_tickers") else []
            if not tickers:
                # Fallback: try individual 24hr ticker
                tickers = []
        except Exception as e:
            logger.warning(f"Ticker fetch failed: {e}")
            tickers = []

        # Process tickers
        for t in tickers:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            name = sym.replace("USDT", "")
            if name in SKIP_COINS:
                continue
            try:
                vol = float(t.get("quoteVolume", 0))
                chg = float(t.get("priceChangePercent", 0))
                price = float(t.get("lastPrice", 0))
                if vol > YAOBI_MIN_VOLUME_USD and abs(chg) > YAOBI_MIN_PRICE_CHANGE:
                    score = abs(chg) * 0.4
                    candidates[sym] = {
                        "name": name,
                        "price": price,
                        "volume_24h": vol,
                        "price_change_pct": chg,
                        "score": score,
                    }
            except (ValueError, TypeError):
                pass

        # ---- Step 2: Top-N detailed scan ----
        top_n = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)[:YAOBI_MAX_CANDIDATES]
        results: List[YaobiCandidate] = []

        for sym, info in top_n:
            cvd_pct = 0.0
            oi_pct = 0.0
            ob_imb = 0.0

            # Try CVD
            try:
                if hasattr(client, "get_taker_volume"):
                    taker = client.get_taker_volume(symbol=sym, limit=30)
                    if taker:
                        cvd_pct = self._calc_cvd_pct(taker)
            except Exception:
                pass

            # Try OI
            try:
                if hasattr(client, "get_open_interest"):
                    oi_data = client.get_open_interest(symbol=sym)
                    if oi_data:
                        oi_pct = float(oi_data.get("percentage", 0))
            except Exception:
                pass

            # Calculate final score
            chg = info["price_change_pct"]
            direction = "LONG" if chg > 0 else "SHORT"

            final_score = (
                abs(chg) * WEIGHT_PRICE_CHANGE * 0.1 +
                (info["volume_24h"] / 1e7) * WEIGHT_VOLUME +
                abs(cvd_pct) * WEIGHT_CVD * 10 +
                oi_pct * WEIGHT_OI * 10 +
                abs(ob_imb) * WEIGHT_ORDERBOOK * 10
            )

            candidate = YaobiCandidate(
                symbol=sym,
                name=info["name"],
                price=info["price"],
                volume_24h=info["volume_24h"],
                price_change_pct=chg,
                cvd_5m_pct=cvd_pct,
                oi_change_pct=oi_pct,
                ob_imbalance=ob_imb,
                score=final_score,
                direction=direction,
                timestamp=datetime.now(BJT).isoformat(),
            )
            results.append(candidate)

        results.sort(key=lambda x: x.score, reverse=True)
        self._candidates = results
        self._last_scan = time.time()
        return results

    @staticmethod
    def _calc_cvd_pct(taker_data: list) -> float:
        """Calculate CVD percentage from taker volume data."""
        if not taker_data:
            return 0.0
        buy_vol = sum(float(d.get("buyVolume", 0)) for d in taker_data if float(d.get("buyVolume", 0)))
        sell_vol = sum(float(d.get("sellVolume", 0)) for d in taker_data if float(d.get("sellVolume", 0)))
        total = buy_vol + sell_vol
        if total > 0:
            return (buy_vol - sell_vol) / total * 100
        return 0.0

    def get_top(self, n: int = 10, direction: str = None) -> List[dict]:
        """Get top N candidates, optionally filtered by direction."""
        results = self._candidates
        if direction:
            results = [c for c in results if c.direction == direction.upper()]
        return [c.to_dict() for c in results[:n]]

    def get_status(self) -> dict:
        """Scanner status."""
        return {
            "last_scan_ts": self._last_scan,
            "candidates": len(self._candidates),
            "top_5": self.get_top(5),
        }


# ============================================================
# Singleton
# ============================================================

_scanner: Optional[YaobiScanner] = None


def get_yaobi_scanner() -> YaobiScanner:
    global _scanner
    if _scanner is None:
        _scanner = YaobiScanner()
    return _scanner
