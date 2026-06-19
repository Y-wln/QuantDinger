"""DAG Consensus V2 - Multi-signal voting from MerCu data (relaxed)."""
import logging
from typing import Dict, List, Tuple
from .base import BaseStrategy, StrategySignal

logger = logging.getLogger(__name__)

class DAGConsensusV2(BaseStrategy):
    def __init__(self):
        super().__init__("dag_v2")
        self.min_votes = 1  # Relaxed: only need 1 confirming vote

    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        return []

    def validate(self, signal: StrategySignal, mercu_data: dict) -> Tuple[bool, str, int]:
        direction = signal.direction
        anomalies = mercu_data.get("anomalies", [])
        momentum = mercu_data.get("momentum", {})
        boards = momentum.get("boards", {})

        votes_bull = 0; votes_bear = 0; details = []
        sym = signal.symbol.upper()

        # Vote 1: Check anomaly confirmation
        for a in anomalies:
            a_sym = (a.get("symbol") or a.get("sym","").replace("$","")).upper()
            if a_sym != sym: continue
            d = a.get("main_direction", 0); dim = a.get("main_dim", "")
            grade = a.get("grade", "")
            if dim == "oi" and d > 0 and grade == "SS":
                votes_bull += 1; details.append("OI暴买")
            elif dim == "oi" and d < 0 and grade == "SS":
                votes_bear += 1; details.append("OI暴卖")
            elif dim == "vol" and grade == "SS":
                if d > 0: votes_bull += 1; details.append("Vol暴买")
                else: votes_bear += 1; details.append("Vol暴卖")
            break

        # Vote 2: Check momentum boards
        for side_key, bull_bear in [("priceUp","bull"), ("priceDown","bear")]:
            for item in boards.get(side_key, []):
                if item.get("sym","").upper() != sym: continue
                if bull_bear == "bull": votes_bull += 1; details.append(f"动量共振{item.get('resonance',[])}")
                else: votes_bear += 1; details.append(f"动量下跌")
                break

        if direction == "LONG":
            my_votes = votes_bull; opp_votes = votes_bear
        else:
            my_votes = votes_bear; opp_votes = votes_bull

        consensus = my_votes - opp_votes

        if my_votes < self.min_votes:
            return False, f"投票不足({my_votes}<{self.min_votes})", consensus
        if opp_votes > my_votes:
            return False, f"反对票胜({opp_votes}>{my_votes})", consensus

        return True, f"共识{my_votes}票", consensus

    def filter_signals(self, signals: List[StrategySignal], mercu_data: dict) -> List[StrategySignal]:
        passed = []
        for sig in signals:
            ok, reason, cs = self.validate(sig, mercu_data)
            sig.reasons.append(f"DAG:{reason}")
            sig.score = sig.score + cs * 2
            if ok: passed.append(sig)
        return passed
