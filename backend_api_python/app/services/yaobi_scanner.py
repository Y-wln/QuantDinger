"""Yaobi Scanner V2 - Uses MerCu data (no Binance dependency)."""
from __future__ import annotations

import os, time, threading, logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

YAOBI_MIN_SCORE = int(os.getenv("YAOBI_MIN_SCORE", "5"))
YAOBI_SCAN_INTERVAL = int(os.getenv("YAOBI_SCAN_INTERVAL", "60"))
YAOBI_MAX_CANDIDATES = int(os.getenv("YAOBI_MAX_CANDIDATES", "30"))
SKIP_COINS = frozenset({"BTC","ETH","SOL","BNB","XRP","ADA","DOGE","DOT","LINK","AVAX","LTC","USDC","USDT"})

@dataclass
class YaobiCandidate:
    symbol: str; price: float = 0; volume_pct: float = 0; oi_pct: float = 0
    score: float = 0; direction: str = "NEUTRAL"; signals: List[str] = field(default_factory=list)
    timestamp: str = ""
    def to_dict(self) -> dict:
        return {"symbol":self.symbol,"price":self.price,"volume_pct":round(self.volume_pct,1),
                "oi_pct":round(self.oi_pct,1),"score":round(self.score,1),
                "direction":self.direction,"signals":self.signals,"timestamp":self.timestamp}

class YaobiScanner:
    def __init__(self):
        self._candidates: List[YaobiCandidate] = []
        self._last_scan: float = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="yaobi-scan")
        self._thread.start()
        logger.info("YaobiScanner V2 started (MerCu-powered)")

    def stop(self):
        self._running = False
        if self._thread: self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try: self.scan()
            except Exception as e: logger.warning(f"Yaobi scan error: {e}")
            time.sleep(YAOBI_SCAN_INTERVAL)

    def scan(self) -> List[YaobiCandidate]:
        from app.data_providers.hermes_mercu import get_hermes_engine
        engine = get_hermes_engine()
        data = engine.get_all_data()
        anomalies = data.get("anomalies", [])
        momentum = data.get("momentum", {})
        surge = data.get("surge", [])

        results = []
        seen = set()

        # Process anomalies (volume bursts, OI changes)
        for a in anomalies[:100]:
            sym = a.get("sym","").replace("$","")
            if not sym or sym in SKIP_COINS or sym in seen: continue
            seen.add(sym)
            score = 0; signals = []; direction = "NEUTRAL"
            grade = a.get("grade",""); dim = a.get("main_dim","")
            d = a.get("main_direction",0); pct = abs(a.get("pct_to_ref",0))
            val = a.get("main_value",0)

            if dim == "oi":
                if d > 0: signals.append(f"OI+{abs(val/1e6):.1f}M"); score += 4; direction = "LONG"
                else: signals.append(f"OI-{abs(val/1e6):.1f}M"); score += 3; direction = "SHORT"
            elif dim == "vol":
                signals.append(f"Vol{abs(pct):.0f}%"); score += 3
                if "buy" in a.get("main_dim_label","").lower(): direction = "LONG"
                elif "sell" in a.get("main_dim_label","").lower(): direction = "SHORT"
            if "SS" in grade: score += 3
            elif "S" in grade: score += 1
            if pct > 50: score += 3
            elif pct > 20: score += 1

            price = float(a.get("price",0)) or float(a.get("last_price",0))
            results.append(YaobiCandidate(
                symbol=sym, price=price, volume_pct=pct if dim=="vol" else 0,
                oi_pct=pct if dim=="oi" else 0, score=score, direction=direction,
                signals=signals, timestamp=datetime.now(BJT).isoformat()))

        # Add surge data
        for s in surge[:10]:
            sym = s.get("symbol","")
            if not sym or sym in SKIP_COINS or sym in seen: continue
            seen.add(sym)
            mult = float(s.get("surge_mult",1))
            signals = [f"Surge x{mult:.1f}"]
            results.append(YaobiCandidate(
                symbol=sym, price=float(s.get("price",0)), volume_pct=float(s.get("vol_pct",0)),
                score=min(mult*5,15), direction="LONG" if mult>1 else "SHORT",
                signals=signals, timestamp=datetime.now(BJT).isoformat()))

        results.sort(key=lambda x: x.score, reverse=True)
        self._candidates = results[:YAOBI_MAX_CANDIDATES]
        self._last_scan = time.time()
        if results: logger.info(f"Yaobi scan: {len(results)} candidates, top={results[0].symbol} score={results[0].score}")
        return self._candidates

    def get_top(self, n=10, direction=None):
        r = self._candidates
        if direction: r = [c for c in r if c.direction==direction.upper()]
        return [c.to_dict() for c in r[:n]]

    def get_status(self):
        return {"last_scan_ts":self._last_scan,"candidates":len(self._candidates),"top_5":self.get_top(5)}

_scanner: Optional[YaobiScanner] = None
def get_yaobi_scanner() -> YaobiScanner:
    global _scanner
    if _scanner is None: _scanner = YaobiScanner(); _scanner.start()
    return _scanner
