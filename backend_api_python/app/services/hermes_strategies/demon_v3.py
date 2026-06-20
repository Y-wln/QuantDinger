"""Demon V3 - Document-based early entry strategy.

Uses ALL signals from 《山寨币庄家异动数据库 V1》:
- Phase 1: Early/leading signals (pre-move detection)
- Phase 2: Stage classification (accumulation/washout/breakout/etc.)
- Phase 3: Entry timing via composite indicators
- Phase 4: Risk-adjusted scoring

Key difference from V2: detects accumulation BEFORE breakout,
not after OI extremes have already happened.
"""
import logging
from typing import Dict, List
from .base import BaseStrategy, StrategySignal
from .indicators import (
    momentum_score, surge_score, plaza_score, 
    oi_flow_score, cvd_proxy_score, composite_score, interpret_score
)
from .early_signals import run_all_early_signals, get_early_entry_score

logger = logging.getLogger(__name__)
SKIP_COINS = frozenset({"BTC","ETH","SOL","BNB","XRP","ADA","DOGE","DOT","LINK","AVAX","LTC","USDC","USDT"})

class DemonV3(BaseStrategy):
    """Demon V3 - Document-driven pre-positioning strategy.
    
    Three entry modes:
    - Accumulate: early signals present, build small position
    - Entry: stage confirms breakout, full position
    - Exit: distribution/crash detected, close
    """
    def __init__(self):
        super().__init__("demon_v3")

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        signals = []
        anomalies = mercu_data.get("anomalies", [])
        indicators = mercu_data.get("indicators", {})
        seen = set()

        for a in anomalies[:60]:
            sym = (a.get("symbol") or a.get("sym","").replace("$","")).upper()
            if not sym or sym in SKIP_COINS or sym in seen:
                continue
            seen.add(sym)

            reasons = []
            score = 0
            direction = "NEUTRAL"

            # ── Phase 1: Run ALL document-based early signals ──
            early_signals, stage = run_all_early_signals(sym, mercu_data, indicators)
            early_score = sum(s.score for s in early_signals)
            
            # Record all early signal evidence
            for es in early_signals:
                reasons.append(f"{es.name}({es.score:+d})")
            
            # ── Phase 2: Stage-based scoring ──
            if stage.stage == "accumulation":
                score += max(early_score, 5)
                direction = "LONG"
                reasons.insert(0, f"【吸筹期】")
            elif stage.stage == "washout":
                if stage.entry_zone == "entry":
                    score += 6
                    direction = "LONG"
                    reasons.insert(0, f"【洗盘结束】")
                else:
                    score += 3
                    direction = "LONG"
                    reasons.insert(0, f"【洗盘期观察】")
            elif stage.stage == "breakout":
                score += early_score + 2
                direction = "LONG" if early_score > 0 else "SHORT"
                reasons.insert(0, f"【主升确认】")
            elif stage.stage == "blowoff":
                score -= 6
                direction = "SHORT"
                reasons.insert(0, f"【赶顶风险】")
            elif stage.stage == "distribution":
                score -= max(abs(early_score), 5)
                direction = "SHORT"
                reasons.insert(0, f"【派发期】")
            elif stage.stage == "crash":
                score -= 8
                direction = "SHORT"
                reasons.insert(0, f"【崩盘期】")
            else:
                # Neutral stage: fall back to classic OI detection
                dim = a.get("main_dim","")
                d = a.get("main_direction",0)
                grade = a.get("grade","")
                percentile = float(a.get("percentile",0))
                rank = a.get("self_history_rank",99)

                if dim == "oi" and d < 0 and grade == "SS" and rank <= 3:
                    score += 8; reasons.append(f"OI暴跌#{rank}→反弹")
                    direction = "LONG"
                elif dim == "oi" and d > 0 and grade == "SS" and rank <= 3:
                    score -= 6; reasons.append(f"OI暴涨#{rank}→回落")
                    direction = "SHORT"
                elif dim == "oi" and d > 0 and percentile > 0.95:
                    score += 4; reasons.append(f"OI吸筹p{percentile:.0%}")
                    direction = "LONG"
                elif dim == "oi" and d < 0 and percentile > 0.95:
                    score -= 4; reasons.append(f"OI派发p{percentile:.0%}")
                    direction = "SHORT"

            # ── Phase 3: Indicator confirmations ──
            if direction != "NEUTRAL":
                # Surge rhythm
                sg = surge_score(sym, indicators)
                if sg.direction == direction:
                    score += abs(sg.score) // 2
                    if sg.reason: reasons.append(f"⚡{sg.reason}")
                elif sg.direction != "NEUTRAL":
                    score -= abs(sg.score) // 3
                    reasons.append("⚠️surge分歧")

                # Plaza smart money
                pl = plaza_score(sym, indicators)
                if pl.direction == direction:
                    score += abs(pl.score)
                    if pl.reason: reasons.append(f"Plaza:{pl.reason}")
                elif pl.direction != "NEUTRAL":
                    score -= 1

                # CVD proxy
                cv = cvd_proxy_score(sym, indicators, anomalies)
                if cv.direction == direction:
                    score += cv.score
                    if cv.reason: reasons.append(f"CVD:{cv.reason}")

                # Momentum
                mom = momentum_score(sym, indicators)
                if mom.direction == direction:
                    score += mom.score // 2
                    if mom.reason: reasons.append(mom.reason)

                # Composite cross-check
                comp, comp_dir, comp_reasons = composite_score(sym, mercu_data, indicators)
                if comp_dir == direction:
                    score += comp // 3
                    if abs(comp) >= 15:
                        reasons.append("多指标共振")
                elif comp_dir != "NEUTRAL" and abs(comp) > abs(score):
                    score = score // 2
                    reasons.append("⚠️综合分歧")

            if direction == "NEUTRAL":
                continue

            stage_label = interpret_score(score)
            confidence = "high" if abs(score) >= 20 else "medium" if abs(score) >= 10 else "low"

            signals.append(StrategySignal(
                symbol=sym, direction=direction, score=score,
                price=0, stage=stage_label, reasons=reasons,
                source=self.name, confidence=confidence
            ))

        return signals
