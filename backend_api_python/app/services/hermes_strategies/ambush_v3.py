"""Ambush V3 - Pre-positioning strategy using document-based early signals.

Focus: detect accumulation BEFORE breakout.
Key difference from V2: uses stage detection to find coins in
accumulation/washout phase, not just reacting to extremes.
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

class AmbushV3(BaseStrategy):
    """Ambush V3 - Pre-positioning at accumulation/washout phase.
    
    Focus: find coins BEFORE they break out using:
    - Stage classification (优先accumulation/washout)
    - Early signal convergence (3+ early signals = strong)
    - Multi-TF resonance (OI + Vol + Price alignment)
    """
    def __init__(self):
        super().__init__("ambush_v3")

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        signals = []
        anomalies = mercu_data.get("anomalies", [])
        indicators = mercu_data.get("indicators", {})
        rank_data = mercu_data.get("rank", {})
        seen = set()

        for a in anomalies[:60]:
            sym = (a.get("symbol") or a.get("sym","").replace("$","")).upper()
            if not sym or sym in SKIP_COINS or sym in seen:
                continue
            seen.add(sym)

            reasons = []
            score = 0
            direction = "NEUTRAL"

            # ── Phase 1: Early signal detection ──
            early_signals, stage = run_all_early_signals(sym, mercu_data, indicators)
            
            # Count accumulation signals specifically
            acc_signals = [s for s in early_signals if s.stage == "accumulation"]
            acc_count = len(acc_signals)
            
            for es in early_signals:
                reasons.append(f"{es.name}({es.score:+d})")

            # ── Phase 2: Ambush logic - only enter in early stages ──
            if stage.stage == "accumulation" and acc_count >= 2:
                # Strong accumulation: stealth entry
                score += 6 + acc_count * 2
                direction = "LONG"
                reasons.insert(0, f"【埋伏·吸筹】×{acc_count}")
                
            elif stage.stage == "accumulation" and acc_count == 1:
                # Weak accumulation: watch only
                score += 3
                direction = "LONG"
                reasons.insert(0, f"【观察·吸筹建仓】")
                
            elif stage.stage == "washout" and stage.entry_zone == "entry":
                # Washout ending = best entry
                score += 8
                direction = "LONG"
                reasons.insert(0, f"【埋伏·洗盘结束】")
                
            elif stage.stage == "washout":
                # Still washing out: wait
                score += 2
                direction = "LONG"
                reasons.insert(0, f"【观察·洗盘中】")

            # ── Phase 3: Rank-based priority ──
            if direction != "NEUTRAL" and sym in rank_data:
                rank = rank_data.get(sym, {}).get("rank", 99) if isinstance(rank_data.get(sym), dict) else rank_data.get(sym, 99)
                if rank <= 5:
                    score += 2
                    reasons.append(f"🏆排名#{rank}")
                elif rank <= 20:
                    score += 1

            # ── Phase 4: Indicator confirmations ──
            if direction != "NEUTRAL":
                # Vol moderate expansion = early signal confirmation
                vol_early = any("Vol温和" in r for r in reasons)
                if vol_early:
                    score += 2
                    reasons.append("🔍量先行")

                # Surge rhythm
                sg = surge_score(sym, indicators)
                if sg.direction == direction and "加速" in str(sg.reason):
                    score += 3
                    reasons.append(f"⚡{sg.reason}")
                elif sg.direction != "NEUTRAL" and sg.direction != direction:
                    score -= 2

                # Plaza confirmation
                pl = plaza_score(sym, indicators)
                if pl.direction == direction:
                    score += abs(pl.score)
                    if pl.reason: reasons.append(f"Plaza:{pl.reason}")

                # Momentum alignment
                mom = momentum_score(sym, indicators)
                if mom.direction == direction:
                    score += mom.score // 2
                    if mom.reason: reasons.append(mom.reason)
                elif mom.direction != "NEUTRAL":
                    score -= 1

                # Composite check
                comp, comp_dir, comp_reasons = composite_score(sym, mercu_data, indicators)
                if comp_dir == direction:
                    score += comp // 4
                    if abs(comp) >= 12:
                        reasons.append("多指标共振")

            # ── Phase 5: Exit signals ──
            if stage.stage in ("distribution", "blowoff", "crash"):
                score -= 6
                direction = "SHORT"
                reasons.insert(0, f"【{stage.stage}·退出】")

            if direction == "NEUTRAL":
                continue

            stage_label = interpret_score(score)
            confidence = "high" if acc_count >= 3 else "medium" if acc_count >= 1 else "low"

            signals.append(StrategySignal(
                symbol=sym, direction=direction, score=score,
                price=0, stage=stage_label, reasons=reasons,
                source=self.name, confidence=confidence
            ))

        return signals
