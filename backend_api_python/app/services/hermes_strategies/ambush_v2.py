"""Ambush V2 - Enhanced: early accumulation + surge + rank + resonance.

V3 upgrade: uses all MerCu endpoints for multi-dimensional signal detection.
"""
import logging
from typing import Dict, List
from .base import BaseStrategy, StrategySignal
from .indicators import (
    momentum_score, surge_score, plaza_score,
    oi_flow_score, cvd_proxy_score, composite_score, interpret_score
)

logger = logging.getLogger(__name__)
SKIP_COINS = frozenset({"BTC","ETH","SOL","BNB","XRP","ADA","DOGE","DOT","LINK","AVAX","LTC","USDC","USDT"})

class AmbushV2(BaseStrategy):
    """Ambush V2 - Early accumulation + multi-TF resonance detection.
    
    Uses: OI accumulation patterns + momentum resonance + surge rhythm +
          rank data + plaza smart money + CVD proxy.
    """
    def __init__(self):
        super().__init__("ambush_v2")

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        signals = []
        anomalies = mercu_data.get("anomalies", [])
        momentum = mercu_data.get("momentum", {})
        boards = momentum.get("boards", {})
        indicators = mercu_data.get("indicators", {})
        rank_data = mercu_data.get("rank", {})
        seen = set()

        # Build resonance map
        resonance_map = {}
        for side in ("priceUp", "priceDown"):
            for item in boards.get(side, []):
                sym = item.get("sym","")
                resonance_map[sym] = item.get("resonance", [])

        # Build rank map for cross-sectional comparison
        rank_map = {}
        for item in rank_data.get("data", []):
            sym = item.get("sym", item.get("symbol", ""))
            rank_map[sym] = item.get("rank", 99)

        for a in anomalies[:50]:
            sym = (a.get("symbol") or a.get("sym","").replace("$","")).upper()
            if not sym or sym in SKIP_COINS or sym in seen: continue
            seen.add(sym)

            dim = a.get("main_dim", ""); d = a.get("main_direction", 0)
            grade = a.get("grade", ""); val = abs(a.get("main_value", 0))
            percentile = float(a.get("percentile", 0))

            reasons = []; score = 0; direction = "NEUTRAL"

            # ── Core: OI accumulation with high percentile ──
            if dim == "oi" and d > 0 and percentile > 0.95 and grade in ("SS","S"):
                score += 8; reasons.append(f"OI吸筹p{percentile:.0%}")
                direction = "LONG"
            elif dim == "oi" and d < 0 and percentile > 0.95 and grade in ("SS","S"):
                score -= 6; reasons.append(f"OI派发p{percentile:.0%}")
                direction = "SHORT"

            # Vol burst with resonance = possible breakout
            if dim == "vol" and percentile > 0.90:
                res = resonance_map.get(sym, [])
                if len(res) >= 2:
                    if d > 0:
                        if direction == "LONG": score += 4
                        reasons.append(f"Vol启动+共振{len(res)}TF")
                        direction = "LONG" if direction == "NEUTRAL" else direction
                    else:
                        if direction == "SHORT": score -= 4
                        reasons.append(f"Vol恐慌+共振{len(res)}TF")
                        direction = "SHORT" if direction == "NEUTRAL" else direction

            # ── V3 Enhancement: surge rhythm check ──
            if direction != "NEUTRAL":
                sg = surge_score(sym, indicators)
                if sg.direction == direction and "加速" in str(sg.reason):
                    score += 3
                    reasons.append(f"⚡{sg.reason}")
                elif sg.direction != "NEUTRAL" and sg.direction != direction:
                    score -= 2
                    reasons.append(f"⚠️surge反向")

            # ── V3 Enhancement: rank-based filter ──
            if direction != "NEUTRAL" and sym in rank_map:
                rank = rank_map[sym]
                if rank <= 5:  # Top 5 ranked = strong
                    score += 2
                    reasons.append(f"🏆排名#{rank}")
                elif rank <= 20:
                    score += 1

            # ── V3 Enhancement: plaza smart money ──
            if direction != "NEUTRAL":
                pl = plaza_score(sym, indicators)
                if pl.direction == direction:
                    score += abs(pl.score)
                    if pl.reason: reasons.append(f"Plaza:{pl.reason}")

            # ── V3 Enhancement: momentum confirmation ──
            if direction != "NEUTRAL":
                mom = momentum_score(sym, indicators)
                if mom.direction == direction:
                    score += mom.score // 2
                    if mom.reason: reasons.append(mom.reason)

            # ── V3 Enhancement: composite cross-check ──
            if direction != "NEUTRAL" and abs(score) >= 6:
                comp, comp_dir, comp_reasons = composite_score(sym, mercu_data, indicators)
                if comp_dir == direction:
                    score += comp // 4
                    if abs(comp) >= 12:
                        reasons.append("多指标共振")

            if direction == "NEUTRAL":
                continue

            stage = interpret_score(score)
            confidence = "high" if abs(score) >= 18 else "medium" if abs(score) >= 10 else "low"

            # Price from momentum
            mom_map = indicators.get("momentum_map", {})
            price = 0.0

            signals.append(StrategySignal(
                symbol=sym, direction=direction, score=score,
                price=price, stage=stage, reasons=reasons,
                source=self.name, confidence=confidence
            ))

        return signals
