"""Demon V2 - Mean reversion on extreme OI/vol moves from MerCu data."""
import logging
from typing import Dict, List
from .base import BaseStrategy, StrategySignal

logger = logging.getLogger(__name__)
SKIP_COINS = frozenset({"BTC","ETH","SOL","BNB","XRP","ADA","DOGE","DOT","LINK","AVAX","LTC","USDC","USDT"})

class DemonV2(BaseStrategy):
    def __init__(self):
        super().__init__("demon_v2")

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        signals = []
        anomalies = mercu_data.get("anomalies", [])
        momentum = mercu_data.get("momentum", {})
        boards = momentum.get("boards", {})
        seen = set()

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
                score += 12; reasons.append(f"OI暴跌#{rank}→反弹"); direction = "LONG"
            elif dim == "oi" and d < 0 and percentile > 0.98:
                score += 8; reasons.append(f"OI急跌p{percentile:.0%}"); direction = "LONG"
            # Extreme OI surge = potential reversal
            elif dim == "oi" and d > 0 and grade == "SS" and rank <= 3:
                score -= 8; reasons.append(f"OI暴涨#{rank}→回落"); direction = "SHORT"
            # Vol extreme
            elif dim == "vol" and grade == "SS" and rank <= 3:
                if d > 0: score -= 6; reasons.append(f"Vol极端#{rank}→回落"); direction = "SHORT"
                else: score += 6; reasons.append(f"Vol恐慌#{rank}→反弹"); direction = "LONG"

            if abs(score) >= 6:
                signals.append(StrategySignal(
                    symbol=sym, direction=direction, score=score,
                    price=0, reasons=reasons, source="demon_v2",
                    confidence="medium"))

        signals.sort(key=lambda x: abs(x.score), reverse=True)
        return signals[:8]
