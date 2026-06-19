"""Ambush V2 - Early accumulation patterns from MerCu data."""
import logging
from typing import Dict, List
from .base import BaseStrategy, StrategySignal

logger = logging.getLogger(__name__)
SKIP_COINS = frozenset({"BTC","ETH","SOL","BNB","XRP","ADA","DOGE","DOT","LINK","AVAX","LTC","USDC","USDT"})

class AmbushV2(BaseStrategy):
    def __init__(self):
        super().__init__("ambush_v2")

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        signals = []
        anomalies = mercu_data.get("anomalies", [])
        momentum = mercu_data.get("momentum", {})
        boards = momentum.get("boards", {})
        seen = set()

        # Build resonance map from momentum
        resonance_map = {}
        for side in ("priceUp", "priceDown"):
            for item in boards.get(side, []):
                sym = item.get("sym","")
                resonance_map[sym] = item.get("resonance", [])

        for a in anomalies[:50]:
            sym = (a.get("symbol") or a.get("sym","").replace("$","")).upper()
            if not sym or sym in SKIP_COINS or sym in seen: continue
            seen.add(sym)

            dim = a.get("main_dim", ""); d = a.get("main_direction", 0)
            grade = a.get("grade", ""); val = abs(a.get("main_value", 0))
            percentile = float(a.get("percentile", 0))

            reasons = []; score = 0; direction = "NEUTRAL"

            # OI building modestly with high percentile = accumulation
            if dim == "oi" and d > 0 and percentile > 0.95 and grade in ("SS","S"):
                score += 8; reasons.append(f"OI吸筹p{percentile:.0%}"); direction = "LONG"
            # OI drop from high level = distribution
            elif dim == "oi" and d < 0 and percentile > 0.95 and grade == "SS":
                score -= 8; reasons.append(f"OI派发p{percentile:.0%}"); direction = "SHORT"
            # Vol burst with high rank = possible breakout start
            elif dim == "vol" and percentile > 0.95 and grade == "SS":
                res = resonance_map.get(sym, [])
                if d > 0: score += 6; reasons.append(f"Vol启动+共振{len(res)}TF"); direction = "LONG"
                else: score -= 6; reasons.append(f"Vol异动"); direction = "SHORT"

            if abs(score) >= 5:
                signals.append(StrategySignal(
                    symbol=sym, direction=direction, score=score,
                    price=0, reasons=reasons, source="ambush_v2",
                    confidence="low"))

        signals.sort(key=lambda x: abs(x.score), reverse=True)
        return signals[:6]
