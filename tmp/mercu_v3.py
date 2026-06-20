"""MerCu Data Bridge V3 - context-aware signal generation based on ????.docx model."""
import json, os, time, glob

DATA_DIR = "/home/ubuntu/scripts/agents/mercu_data"

# Scoring weights from document
SCORE = {
    "????": 5, "????": 4, "????": 5,
    "OI??_5_10": 2, "OI??_10plus": 4,
    "Vol??_10plus": 3, "??????": 4, "?????": 3,
    "??????": 2, "?????": -1, "?????": -4,
    "????": -6, "OI??": -5, "?????": -4,
    "OI??_10plus": -4, "????": -5,
}

# Context-dependent interpretation: signal -> (low_meaning, high_meaning, low_score, high_score)
SIGNAL_CONTEXT = {
    "OI??": ("??/??", "????", 4, -2),
    "OI??": ("????", "??/??", 2, -5),
    "Vol??": ("??/??", "??/??", 3, -3),
    "????": ("????", "????", 5, -3),
    "????": ("????", "????", -3, 5),
}

# Stage score thresholds from document
STAGE_THRESHOLDS = [
    (12, "????", "strong_long"),
    (8, "????", "long"),
    (4, "??/??", "weak_long"),
    (0, "??", "neutral"),
    (-5, "???", "weak_short"),
    (-100, "??/??", "short"),
]


class MerCuBridgeV3:
    """Context-aware MerCu signal generator."""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self._price_cache = {}
        self._price_ts = 0

    def _read_file(self, filename):
        fpath = os.path.join(self.data_dir, filename)
        if not os.path.exists(fpath):
            return {}
        try:
            with open(fpath) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def is_fresh(self, max_age=120):
        fpath = os.path.join(self.data_dir, "anomaly-v4_100.json")
        if not os.path.exists(fpath):
            return False
        return (time.time() - os.path.getmtime(fpath)) < max_age

    # ?? price context ??
    def _get_price_context(self, symbol):
        """Determine if coin is at relative high, low, or mid."""
        now = time.time()
        if now - self._price_ts > 300:
            self._price_cache = {}
            mom = self._read_file("momentum_4h.json")
            boards = mom.get("boards", {})
            for side in ("priceUp", "priceDown"):
                for item in boards.get(side, []):
                    sym = item.get("sym", "")
                    val_str = item.get("val", "0%")
                    try:
                        val = float(val_str.replace("%", "").replace("+", ""))
                    except ValueError:
                        val = 0
                    self._price_cache[sym] = val * (1 if side == "priceUp" else -1)
            self._price_ts = now

        pct = self._price_cache.get(symbol.replace("USDT", ""), 0)
        if pct > 8:
            return "high"
        elif pct < -8:
            return "low"
        elif pct > 3:
            return "mid_high"
        elif pct < -3:
            return "mid_low"
        else:
            return "mid"

    # ?? anomaly parsing ??
    def get_anomalies(self, limit=100):
        data = self._read_file("anomaly-v4_100.json")
        return data.get("data", [])[:limit]

    def get_plaza_sentiment(self, symbol):
        """Get plaza crowd sentiment for a symbol."""
        data = self._read_file("plaza.json")
        sym_clean = symbol.replace("USDT", "")
        for item in data.get("data", []):
            if item.get("symbol") == sym_clean:
                return {
                    "sentiment": item.get("sentiment", "mixed"),
                    "bullPct": item.get("bullPct", 50),
                    "bearPct": item.get("bearPct", 50),
                    "lsrGlobal": item.get("lsrGlobal", 1.0),
                    "aiSummary": item.get("aiSummary", ""),
                }
        return {}

    def get_surge_items(self, limit=10):
        data = self._read_file("surge_5.json")
        return data.get("items", [])[:limit]

    def get_rank_data(self, symbol):
        """Get hot ranking + AI analysis for a symbol."""
        data = self._read_file("rank.json")
        sym_clean = symbol.replace("USDT", "")
        for item in data.get("top", []):
            if item.get("sym", "").replace("$", "") == sym_clean:
                return item
        return {}

    # ?? signal generation ??
    def analyze_coin(self, symbol):
        """Generate context-aware signal for one coin."""
        sym_clean = symbol.replace("USDT", "")
        anomalies = self.get_anomalies(100)
        context = self._get_price_context(symbol)
        plaza = self.get_plaza_sentiment(symbol)
        rank = self.get_rank_data(symbol)
        surge_items = self.get_surge_items(20)
        surge_syms = {s["sym"] for s in surge_items}

        score = 0
        reasons = []
        details = {}

        # Process anomalies for this coin
        coin_anomalies = [a for a in anomalies if a.get("sym", "").replace("$", "") == sym_clean]
        for a in coin_anomalies:
            dim = a.get("main_dim", "")
            direction = a.get("main_direction", 0)
            amount = a.get("main_amount", 0)
            window = a.get("main_window", "?")
            percentile = a.get("percentile", 0)
            grade = a.get("grade", "")

            # OI signals
            if dim == "oi":
                oi_pct = abs(amount) / 1e6  # rough percentage
                if direction > 0:
                    if context in ("low", "mid_low"):
                        score += 4
                        reasons.append(f"OI??(??){window}")
                    elif context in ("high", "mid_high"):
                        score -= 2
                        reasons.append(f"OI??(????){window}")
                    else:
                        score += 2
                        reasons.append(f"OI??{window}")
                else:
                    if context in ("high", "mid_high"):
                        score -= 5
                        reasons.append(f"OI??(??){window}")
                    elif context in ("low", "mid_low"):
                        score += 2
                        reasons.append(f"OI??(??){window}")
                    else:
                        score -= 3
                        reasons.append(f"OI??{window}")

            # Volume signals
            if dim == "vol":
                if direction > 0:
                    if context in ("low", "mid_low"):
                        score += 3
                        reasons.append(f"Vol??(??){window}")
                    elif context in ("high", "mid_high"):
                        score -= 3
                        reasons.append(f"Vol??(??){window}")
                    else:
                        score += 1
                        reasons.append(f"Vol??{window}")

            details[f"{dim}_{window}"] = {
                "amount": amount,
                "direction": direction,
                "grade": grade,
                "percentile": percentile,
            }

        # Surge bonus
        if sym_clean in surge_syms:
            for s in surge_items:
                if s["sym"] == sym_clean:
                    rhythm = s.get("rhythm", "")
                    if rhythm == "????" and s.get("dir") == "up":
                        if context in ("low", "mid_low"):
                            score += 3
                            reasons.append("Surge????(??)")
                        else:
                            score += 1
                            reasons.append("Surge??")

        # Plaza sentiment overlay
        if plaza:
            bull = plaza.get("bullPct", 50)
            bear = plaza.get("bearPct", 50)
            if bear > 60 and context in ("high", "mid_high"):
                score -= 2
                reasons.append("Plaza??(??)")
            elif bull > 60 and context in ("low", "mid_low"):
                score += 2
                reasons.append("Plaza??(??)")

        # Rank AI analysis
        if rank:
            ai = rank.get("ai", "")
            if "??" in ai or "??" in ai:
                score += 3
                reasons.append("AI:????")
            elif "??" in ai or "??" in ai:
                score -= 3
                reasons.append("AI:????")

        # Determine stage and direction
        stage = "??"
        signal_type = "neutral"
        for threshold, stage_name, sig_type in STAGE_THRESHOLDS:
            if score >= threshold:
                stage = stage_name
                signal_type = sig_type
                break

        direction = "long" if score > 0 else "short" if score < 0 else "neutral"

        return {
            "symbol": symbol,
            "score": score,
            "direction": direction,
            "signal_type": signal_type,
            "stage": stage,
            "context": context,
            "reasons": reasons,
            "details": details,
            "plaza": plaza,
        }

    def get_coin_signals(self, min_abs_score=3):
        """Scan all coins with anomalies and generate signals."""
        anomalies = self.get_anomalies(100)
        surge = self.get_surge_items(20)

        # Collect unique symbols from anomalies + surge
        symbols = set()
        for a in anomalies:
            sym = a.get("sym", "").replace("$", "")
            if sym:
                symbols.add(sym + "USDT")
        for s in surge:
            sym = s.get("sym", "")
            if sym:
                symbols.add(sym + "USDT")

        signals = []
        for sym in symbols:
            result = self.analyze_coin(sym)
            if abs(result["score"]) >= min_abs_score:
                signals.append(result)

        return sorted(signals, key=lambda x: -abs(x["score"]))

    def get_top_signals(self, limit=8):
        """Get top signals for feed."""
        return self.get_coin_signals()[:limit]
