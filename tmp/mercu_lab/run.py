"""mercu-lab v2: strictly follows signal-meaning document rules.
Reconstructs mercu.win labels from raw API data using document rules.
"""
import json, os, time, sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# ============================================================
# DOCUMENT RULES (verbatim)
# ============================================================

# --- OI变化百分比规则 (from document section 3) ---
def classify_oi(pct_abs, window):
    """Classify OI change by document thresholds. Returns (label, score)."""
    if window == "5m":
        if pct_abs < 2: return ("噪音", 0)
        elif pct_abs < 5: return ("有资金进场", 1)
        elif pct_abs < 8: return ("明显异动", 2)
        elif pct_abs < 12: return ("强操盘", 3)
        else: return ("拉盘/砸盘前兆", 4)
    elif window == "15m":
        if pct_abs < 3: return ("轻度异动", 0)
        elif pct_abs < 5: return ("轻度建仓", 1)
        elif pct_abs < 10: return ("主力动作", 3)
        elif pct_abs < 15: return ("主升/逼空", 4)
        else: return ("妖币级别异动", 5)
    else:  # 1h
        if pct_abs < 5: return ("轻度变化", 0)
        elif pct_abs < 10: return ("趋势增强", 2)
        elif pct_abs < 20: return ("强控盘", 4)
        elif pct_abs < 30: return ("妖币启动", 6)
        else: return ("极端行情", 8)

# --- Stage detection rules (from document section 4) ---
# Each stage = combination of conditions
# We detect stages by checking accumulated signals

# --- Scoring weights (from document section 5) ---
SIGNAL_SCORES = {
    "底部吸筹": 5,
    "现货托底": 4,
    "多头共振": 5,
    "OI暴涨_5_10": 2,
    "OI暴涨_10plus": 4,
    "Vol爆发_10plus": 3,
    "大笔买入挂单": 4,
    "空头被挤压": 3,
    "中陷阱后拉回": 2,
    "高陷阱单次": -1,
    "连续高陷阱": -4,
    "顶部派发": -6,
    "OI背离": -5,
    "现货净流出": -4,
    "OI暴跌_10plus": -4,
    "多头爆仓": -5,
}

STAGE_THRESHOLDS = [
    (12, "主升确认", "buy"),
    (8, "偏多启动", "buy"),
    (4, "吸筹/试盘", "watch"),
    (0, "震荡", "wait"),
    (-5, "风险区", "watch_short"),
    (-100, "派发/出货", "sell"),
]

# ============================================================
# DATA READER
# ============================================================
class MerCuReader:
    def __init__(self, data_dir="/home/ubuntu/scripts/agents/mercu_data"):
        self.data_dir = data_dir

    def read(self, filename):
        fpath = os.path.join(self.data_dir, filename)
        if not os.path.exists(fpath):
            return {}
        with open(fpath) as f:
            return json.load(f)

    def get_anomalies(self):
        return self.read("anomaly-v4_100.json").get("data", [])

    def get_momentum_4h(self):
        return self.read("momentum_4h.json")

    def get_surge(self):
        return self.read("surge_5.json")

    def get_rank(self):
        return self.read("rank.json")

    def is_fresh(self):
        fpath = os.path.join(self.data_dir, "anomaly-v4_100.json")
        return os.path.exists(fpath) and (time.time() - os.path.getmtime(fpath) < 120)


# ============================================================
# PRICE CONTEXT (from 4h momentum)
# ============================================================
class PriceContext:
    def __init__(self):
        self._cache = {}
        self._ts = 0

    def get(self, symbol, reader):
        now = time.time()
        if now - self._ts > 300:
            self._cache = {}
            mom = reader.get_momentum_4h()
            for side in ("priceUp", "priceDown"):
                for item in mom.get("boards", {}).get(side, []):
                    sym = item.get("sym", "")
                    try:
                        val = float(item.get("val", "0%").replace("%", "").replace("+", ""))
                    except ValueError:
                        val = 0
                    self._cache[sym] = val * (1 if side == "priceUp" else -1)
            self._ts = now
        pct = self._cache.get(symbol.replace("USDT", ""), 0)
        if pct > 8: return "high"
        elif pct < -8: return "low"
        elif pct > 3: return "mid_high"
        elif pct < -3: return "mid_low"
        return "mid"


# ============================================================
# STATE TRACKER
# ============================================================
@dataclass
class CoinState:
    symbol: str
    total_score: float = 0
    signals: List[str] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)
    stage: str = "震荡"
    last_update: float = 0
    context: str = "mid"
    oi_events_5m: int = 0
    oi_events_15m: int = 0
    oi_events_1h: int = 0
    vol_events: int = 0
    surge_events: int = 0


class StateTracker:
    def __init__(self):
        self.states: Dict[str, CoinState] = {}

    def get(self, symbol):
        if symbol not in self.states:
            self.states[symbol] = CoinState(symbol=symbol, last_update=time.time())
        return self.states[symbol]

    def update(self, symbol, label, score, context, event):
        state = self.get(symbol)
        now = time.time()

        # Decay: score fades over time
        elapsed_min = (now - state.last_update) / 60
        decay = 0.03 * elapsed_min
        if state.total_score > 0:
            state.total_score = max(0, state.total_score - decay)
        else:
            state.total_score = min(0, state.total_score + decay)

        state.total_score += score
        if label not in state.signals:
            state.signals.append(label)
        state.events.append(event)
        state.context = context
        state.last_update = now

        # Count event types
        dim = event.get("dim", "")
        window = event.get("window", "")
        if dim == "oi":
            if window == "5m": state.oi_events_5m += 1
            elif window == "15m": state.oi_events_15m += 1
            else: state.oi_events_1h += 1
        elif dim == "vol":
            state.vol_events += 1

        # --- Stage detection (from document section 4) ---
        signals_set = set(state.signals)
        has_bottom = any(s in signals_set for s in ["低位OI=吸筹", "低位Vol=点火", "Surge极速冒头"])
        has_top = any(s in signals_set for s in ["高位OI=追高", "高位Vol=派发", "连续高陷阱"])
        has_oi_up = state.oi_events_5m + state.oi_events_15m + state.oi_events_1h > 0
        has_vol = state.vol_events > 0

        # Determine stage
        if has_top and state.total_score <= -5:
            state.stage = "派发/出货"
        elif has_top and state.total_score < 0:
            state.stage = "风险区"
        elif has_bottom and state.total_score >= 8:
            state.stage = "偏多启动"
        elif has_bottom and state.total_score >= 4:
            state.stage = "吸筹/试盘"
        elif abs(state.total_score) < 3:
            state.stage = "震荡"
        elif state.total_score >= 8:
            state.stage = "偏多启动"
        elif state.total_score <= -5:
            state.stage = "风险区"

        return state

    def get_signals(self, min_score=4):
        now = time.time()
        active = []
        for sym, state in self.states.items():
            age = now - state.last_update
            if age < 3600 and abs(state.total_score) >= min_score:
                active.append(state)
        return sorted(active, key=lambda s: -abs(s.total_score))


# ============================================================
# DOCUMENT SCORER
# ============================================================
class DocumentScorer:
    def __init__(self, reader, price_ctx, tracker):
        self.reader = reader
        self.price_ctx = price_ctx
        self.tracker = tracker
         self._scored_ids = set()

    def score_anomaly(self, a):
        sym = a.get("sym", "").replace("$", "")
        if not sym:
            return None
        symbol = sym + "USDT"
        dim = a.get("main_dim", "")
        direction = a.get("main_direction", 0)
        window = a.get("main_window", "5m")
        pct = a.get("pct_to_ref", 0)
        pct_abs = abs(pct)
        grade = a.get("grade", "")
        duration = a.get("duration_sec", 0)
        context = self.price_ctx.get(symbol, self.reader)

        label = None
        score = 0

        if dim == "oi":
            oi_label, base_score = classify_oi(pct_abs, window)
            if direction > 0:  # OI increase
                if context in ("high", "mid_high"):
                    label = "高位OI=追高"
                    score = -base_score * 1.5
                elif context in ("low", "mid_low"):
                    label = "低位OI=吸筹"
                    score = base_score * 2.0
                else:
                    label = f"OI增加({oi_label})"
                    score = base_score
            else:  # OI decrease
                if context in ("high", "mid_high"):
                    label = "高位OI跌=出货"
                    score = -base_score * 2.0
                elif context in ("low", "mid_low"):
                    label = "低位OI跌=洗盘"
                    score = base_score * 0.5
                else:
                    label = f"OI减少({oi_label})"
                    score = -base_score * 0.5

        elif dim == "vol":
            if context in ("high", "mid_high"):
                label = "高位Vol=派发"
                score = -3
            elif context in ("low", "mid_low"):
                label = "低位Vol=点火"
                score = +4
            else:
                label = "Vol放大"
                score = +1

        if label is None:
             return None
             eid = sym + "_" + dim + "_" + str(a.get("first_seen_ts",0))
             if eid in self._scored_ids:
                 return None
             self._scored_ids.add(eid)
        
            return None

        # Grade multiplier
        if grade == "SS":
            score *= 1.5
        elif grade == "S":
            score *= 1.2

        # Duration bonus
        if duration > 300:
            score *= 1.2

        score = round(score, 1)

        event = {
            "ts": time.time(), "dim": dim, "direction": direction,
            "pct": pct, "grade": grade, "window": window,
            "duration": duration, "context": context,
            "label": label, "score": score,
        }

        state = self.tracker.update(symbol, label, score, context, event)

        return {
            "symbol": symbol,
            "label": label,
            "score_delta": score,
            "total_score": round(state.total_score, 1),
            "stage": state.stage,
            "direction": "long" if state.total_score > 0 else "short" if state.total_score < 0 else "neutral",
            "context": context,
            "signals": state.signals[-5:],
            "events": len(state.events),
        }

    def score_all(self):
        results = []
        for a in self.reader.get_anomalies():
            r = self.score_anomaly(a)
            if r and abs(r["score_delta"]) >= 0.3:
                results.append(r)
        return sorted(results, key=lambda x: -abs(x["total_score"]))

    def get_signals(self, min_score=4):
        states = self.tracker.get_signals(min_score)
        return [{
            "symbol": s.symbol,
            "direction": "long" if s.total_score > 0 else "short",
            "total_score": round(s.total_score, 1),
            "stage": s.stage,
            "signals": s.signals[-5:],
            "events": len(s.events),
            "context": s.context,
        } for s in states]


# ============================================================
# MAIN
# ============================================================
def run_once(reader, price_ctx, tracker, scorer):
    ts = datetime.now(BJT).strftime("%H:%M:%S")
    results = scorer.score_all()
    signals = scorer.get_signals(min_score=3)

    print(f"[{ts}] {len(results)} events | {len(signals)} signals")
    print("-" * 55)

    # Show events
    for r in results[:12]:
        bar = "+" if r["score_delta"] > 0 else ""
        print(f"  {r['symbol']:12s} {r['score_delta']:+5.1f} total={r['total_score']:+6.1f} "
              f"stage={r['stage']:6s} ctx={r['context']:8s} | {r['label']}")

    # Show signals
    if signals:
        print(f"\n  >>> SIGNALS <<<")
        for s in signals:
            emoji = "LONG" if s["direction"] == "long" else "SHORT"
            print(f"  [{emoji}] {s['symbol']:12s} score={s['total_score']:+5.1f} "
                  f"stage={s['stage']} events={s['events']} signals={s['signals'][:3]}")
    else:
        print(f"  (no signals above threshold)")

    return results, signals


if __name__ == "__main__":
    reader = MerCuReader()
    price_ctx = PriceContext()
    tracker = StateTracker()
    scorer = DocumentScorer(reader, price_ctx, tracker)

    print(f"MerCu Lab v2 | {datetime.now(BJT).strftime('%H:%M:%S')}")
    print(f"Data fresh: {reader.is_fresh()} | Anomalies: {len(reader.get_anomalies())}")
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        print("Live mode: running cycles...")
        cycle = 0
        while True:
            cycle += 1
            if not reader.is_fresh():
                time.sleep(5)
                continue
            print(f"\n--- Cycle {cycle} ---")
            run_once(reader, price_ctx, tracker, scorer)
            time.sleep(30)
    else:
        run_once(reader, price_ctx, tracker, scorer)

        # Show state summary
        print(f"\n=== All Tracked States ===")
        for sym, state in sorted(tracker.states.items(), key=lambda x: -abs(x[1].total_score)):
            if abs(state.total_score) >= 1:
                print(f"  {sym:12s} score={state.total_score:+6.1f} stage={state.stage:6s} "
                      f"signals={state.signals}")
