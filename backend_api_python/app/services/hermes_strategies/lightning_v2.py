"""Lightning V2 - Flash signals from MerCu anomaly + momentum data."""
import time, logging
from typing import Dict, List
from .base import BaseStrategy, StrategySignal, BJT

logger = logging.getLogger(__name__)
COOLDOWN = 600
SKIP_COINS = frozenset({"BTC","ETH","SOL","BNB","XRP","ADA","DOGE","DOT","LINK","AVAX","LTC","USDC","USDT"})

class LightningV2(BaseStrategy):
    def __init__(self):
        super().__init__("lightning_v2")
        self._last_alert: Dict[str, float] = {}

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        signals = []
        anomalies = mercu_data.get("anomalies", [])
        momentum = mercu_data.get("momentum", {})
        boards = momentum.get("boards", {})
        now = time.time()

        # Build price map from momentum boards
        price_map = {}
        for side in ("priceUp", "priceDown"):
            for item in boards.get(side, []):
                sym = item.get("sym", "")
                val_str = item.get("val", "").replace("+","").replace("%","")
                try: price_map[sym] = float(val_str)
                except: pass

        for a in anomalies[:20]:
            sym = (a.get("symbol") or a.get("sym","").replace("$","")).upper()
            if not sym or sym in SKIP_COINS: continue
            if now - self._last_alert.get(sym, 0) < COOLDOWN: continue

            dim = a.get("main_dim", ""); d = a.get("main_direction", 0)
            grade = a.get("grade", ""); val = abs(a.get("main_value", 0))
            percentile = float(a.get("percentile", 0))
            chg_pct = price_map.get(sym, 0)

            score = 0; reasons = []; dir_out = "NEUTRAL"

            if dim == "oi" and d > 0 and grade == "SS" and percentile > 0.95:
                score += 12; reasons.append(f"OI暴买{val/1e6:.1f}M"); dir_out = "LONG"
            elif dim == "oi" and d < 0 and grade == "SS" and percentile > 0.95:
                score -= 12; reasons.append(f"OI暴卖{val/1e6:.1f}M"); dir_out = "SHORT"
            elif dim == "vol" and grade == "SS" and percentile > 0.95:
                if d > 0: score += 10; reasons.append(f"Vol暴买"); dir_out = "LONG"
                else: score -= 10; reasons.append(f"Vol暴卖"); dir_out = "SHORT"

            if abs(score) >= 10:
                self._last_alert[sym] = now
                signals.append(StrategySignal(
                    symbol=sym, direction=dir_out, score=score,
                    price=chg_pct, reasons=reasons, source="lightning_v2",
                    confidence="high"))

        # Add momentum board signals
        for side, dname in [("priceUp","LONG"), ("priceDown","SHORT")]:
            for item in boards.get(side, [])[:8]:
                sym = item.get("sym","").upper()
                if not sym or sym in SKIP_COINS: continue
                if now - self._last_alert.get(sym, 0) < COOLDOWN: continue
                strength = float(item.get("strength", 0))
                resonance = item.get("resonance", [])
                val_str = item.get("val","").replace("+","").replace("%","")
                mc = item.get("mc","")
                if strength < 80: continue
                score = min(int(strength / 10), 12) * (1 if dname=="LONG" else -1)
                reasons = [f"动量{val_str}%", f"共振{len(resonance)}TF", f"MC{mc}"]
                self._last_alert[sym] = now
                signals.append(StrategySignal(
                    symbol=sym, direction=dname, score=score,
                    price=float(val_str) if val_str else 0,
                    reasons=reasons, source="lightning_v2",
                    confidence="high" if len(resonance) >= 3 else "medium"))

        signals.sort(key=lambda x: abs(x.score), reverse=True)
        return signals[:8]
