"""Demon V2 - Enhanced: OI extremes + surge + plaza + CVD proxy.

V3 upgrade: now uses all 9 MerCu endpoints + 5 computed indicators.
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

class DemonV2(BaseStrategy):
    """Demon V2 - Multi-signal convergence strategy.
    
    Uses: OI anomalies (V2 core) + momentum boards + surge rhythm + 
          plaza divergence + CVD proxy + composite scoring.
    """
    def __init__(self):
        super().__init__("demon_v2")

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        signals = []
        anomalies = mercu_data.get("anomalies", [])
        momentum = mercu_data.get("momentum", {})
        boards = momentum.get("boards", {})
        indicators = mercu_data.get("indicators", {})
        seen = set()

        # ── Phase 1: Anomaly-driven signals (original V2 logic) ──
        for a in anomalies[:50]:
            sym = (a.get("symbol") or a.get("sym","").replace("$","")).upper()
            if not sym or sym in SKIP_COINS or sym in seen: continue
            seen.add(sym)

            dim = a.get("main_dim", ""); d = a.get("main_direction", 0)
            grade = a.get("grade", ""); val = abs(a.get("main_value", 0))
            percentile = float(a.get("percentile", 0))
            rank = a.get("self_history_rank", 99)

            reasons = []; score = 0; direction = "NEUTRAL"

            # Extreme OI drop + top rank = potential mean reversion bounce
            if dim == "oi" and d < 0 and grade == "SS" and rank <= 3:
                score += 12; reasons.append(f"OI暴跌#{rank}")
                direction = "LONG"
            elif dim == "oi" and d < 0 and percentile > 0.98:
                score += 8; reasons.append(f"OI急跌p{percentile:.0%}")
                direction = "LONG"
            elif dim == "oi" and d > 0 and grade == "SS" and rank <= 3:
                score -= 8; reasons.append(f"OI暴涨#{rank}")
                direction = "SHORT"
            elif dim == "vol" and grade == "SS" and rank <= 3:
                if d > 0:
                    score -= 6; reasons.append(f"Vol极端#{rank}")
                    direction = "SHORT"
                else:
                    score += 6; reasons.append(f"Vol恐慌#{rank}")
                    direction = "LONG"

            # Moderate signals
            elif dim == "oi" and d > 0 and percentile > 0.95 and grade in ("SS","S"):
                score += 5; reasons.append(f"OI吸筹p{percentile:.0%}")
                direction = "LONG"
            elif dim == "oi" and d < 0 and percentile > 0.95 and grade in ("SS","S"):
                score -= 5; reasons.append(f"OI派发p{percentile:.0%}")
                direction = "SHORT"

            # ── Phase 2: Indicator confirmations (V3 new) ──
            if direction != "NEUTRAL":
                # Surge rhythm confirmation
                sg = surge_score(sym, indicators)
                if sg.direction == direction:
                    score += abs(sg.score) // 2
                    reasons.append(f"⚡{sg.reason}")
                elif sg.direction != "NEUTRAL":
                    score -= abs(sg.score) // 2  # Divergence penalty
                    reasons.append(f"⚠️surge分歧")

                # Plaza smart money confirmation
                pl = plaza_score(sym, indicators)
                if pl.direction == direction:
                    score += abs(pl.score)
                    reasons.append(f"Plaza:{pl.reason}")
                elif pl.direction != "NEUTRAL":
                    score -= 1
                    reasons.append("Plaza分歧")

                # CVD proxy confirmation
                cv = cvd_proxy_score(sym, indicators, anomalies)
                if cv.direction == direction:
                    score += cv.score
                    if cv.reason: reasons.append(f"CVD:{cv.reason}")

                # Momentum board check
                mom = momentum_score(sym, indicators)
                if mom.direction == direction:
                    score += mom.score // 2
                    if mom.reason: reasons.append(mom.reason)

            # ── Phase 3: Composite score integration ──
            if direction != "NEUTRAL":
                comp, comp_dir, comp_reasons = composite_score(sym, mercu_data, indicators)
                if comp_dir == direction:
                    score += comp // 3
                    if abs(comp) >= 15:
                        reasons.append("多指标共振")
                elif comp_dir != "NEUTRAL" and abs(comp) > abs(score):
                    # Composite disagrees strongly - reduce confidence
                    score = score // 2
                    reasons.append("⚠️综合分歧")

            if direction == "NEUTRAL":
                continue

            stage = interpret_score(score)
            confidence = "high" if abs(score) >= 20 else "medium" if abs(score) >= 10 else "low"

            # Get price from momentum board if available
            mom_map = indicators.get("momentum_map", {})
            price = 0.0
            if sym in mom_map:
                # We have momentum data but not exact price
                price = float(a.get("main_value", 0))  # Use OI value as proxy indicator

            signals.append(StrategySignal(
                symbol=sym, direction=direction, score=score,
                price=price, stage=stage, reasons=reasons,
                source=self.name, confidence=confidence
            ))

        return signals
