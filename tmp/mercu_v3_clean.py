import json, os, time, glob

DATA_DIR = "/home/ubuntu/scripts/agents/mercu_data"

SCORE = {
    "\u5e95\u90e8\u5438\u7b79": 5,
    "\u73b0\u8d27\u6258\u5e95": 4,
    "\u591a\u5934\u5171\u632f": 5,
}

SIGNAL_CONTEXT = {
    "OI\u66b4\u6da8": ("\u5efa\u4ed3/\u5438\u7b79", "\u8ffd\u6da8\u63a5\u76d8", 4, -2),
    "OI\u66b4\u8dcc": ("\u6760\u6746\u6e05\u6d17", "\u64a4\u4ed3/\u51fa\u8d27", 2, -5),
    "Vol\u7206\u53d1": ("\u70b9\u706b/\u8bd5\u76d8", "\u6d3e\u53d1/\u7838\u76d8", 3, -3),
    "\u591a\u5934\u5171\u632f": ("\u4e3b\u5347\u542f\u52a8", "\u9ad8\u4f4d\u8bf1\u591a", 5, -3),
    "\u7a7a\u5934\u5171\u632f": ("\u4e0b\u8dcc\u52a0\u901f", "\u4f4e\u4f4d\u8bf1\u7a7a", -3, 5),
}

STAGE_THRESHOLDS = [
    (12, "\u4e3b\u5347\u786e\u8ba4", "strong_long"),
    (8, "\u504f\u591a\u542f\u52a8", "long"),
    (4, "\u5438\u7b79/\u8bd5\u76d8", "weak_long"),
    (0, "\u9707\u8361", "neutral"),
    (-5, "\u98ce\u9669\u533a", "weak_short"),
    (-100, "\u6d3e\u53d1/\u51fa\u8d27", "short"),
]

class MerCuBridgeV3:
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

    def _get_price_context(self, symbol):
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
        if pct > 8: return "high"
        elif pct < -8: return "low"
        elif pct > 3: return "mid_high"
        elif pct < -3: return "mid_low"
        else: return "mid"

    def get_anomalies(self, limit=100):
        data = self._read_file("anomaly-v4_100.json")
        return data.get("data", [])[:limit]

    def get_plaza_sentiment(self, symbol):
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
        data = self._read_file("rank.json")
        sym_clean = symbol.replace("USDT", "")
        for item in data.get("top", []):
            if item.get("sym", "").replace("$", "") == sym_clean:
                return item
        return {}

    def analyze_coin(self, symbol):
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

        coin_anomalies = [a for a in anomalies if a.get("sym", "").replace("$", "") == sym_clean]
        for a in coin_anomalies:
            dim = a.get("main_dim", "")
            direction = a.get("main_direction", 0)
            amount = a.get("main_amount", 0)
            window = a.get("main_window", "?")
            percentile = a.get("percentile", 0)
            grade = a.get("grade", "")

            if dim == "oi":
                if direction > 0:
                    if context in ("low", "mid_low"):
                        score += 4; reasons.append("OI暴涨(吸筹)" + window)
                    elif context in ("high", "mid_high"):
                        score -= 2; reasons.append("OI暴涨(追高风险)" + window)
                    else:
                        score += 2; reasons.append("OI增加" + window)
                else:
                    if context in ("high", "mid_high"):
                        score -= 5; reasons.append("OI暴跌(出货)" + window)
                    elif context in ("low", "mid_low"):
                        score += 2; reasons.append("OI暴跌(洗盘)" + window)
                    else:
                        score -= 3; reasons.append("OI减少" + window)

            if dim == "vol":
                if direction > 0:
                    if context in ("low", "mid_low"):
                        score += 3; reasons.append("Vol爆发(点火)" + window)
                    elif context in ("high", "mid_high"):
                        score -= 3; reasons.append("Vol爆发(派发)" + window)
                    else:
                        score += 1; reasons.append("Vol放大" + window)

            details[dim + "_" + window] = {
                "amount": amount, "direction": direction,
                "grade": grade, "percentile": percentile,
            }

        if sym_clean in surge_syms:
            for s in surge_items:
                if s["sym"] == sym_clean:
                    rhythm = s.get("rhythm", "")
                    if "冒头" in rhythm and s.get("dir") == "up":
                        if context in ("low", "mid_low"):
                            score += 3; reasons.append("Surge极速冒头(启动)")
                        else:
                            score += 1; reasons.append("Surge加速")

        if plaza:
            bull = plaza.get("bullPct", 50)
            bear = plaza.get("bearPct", 50)
            if bear > 60 and context in ("high", "mid_high"):
                score -= 2; reasons.append("Plaza偏空(顶部)")
            elif bull > 60 and context in ("low", "mid_low"):
                score += 2; reasons.append("Plaza偏多(底部)")

        if rank:
            ai = rank.get("ai", "")
            if ai and any(w in ai for w in ["吸筹", "建仓"]):
                score += 3; reasons.append("AI:吸筹信号")
            elif ai and any(w in ai for w in ["派发", "出货"]):
                score -= 3; reasons.append("AI:派发信号")

        stage = "震荡"
        signal_type = "neutral"
        for threshold, stage_name, sig_type in STAGE_THRESHOLDS:
            if score >= threshold:
                stage = stage_name
                signal_type = sig_type
                break

        direction = "long" if score > 0 else "short" if score < 0 else "neutral"
        return {
            "symbol": symbol, "score": score, "direction": direction,
            "signal_type": signal_type, "stage": stage, "context": context,
            "reasons": reasons, "details": details, "plaza": plaza,
        }

    def get_coin_signals(self, min_abs_score=3):
        anomalies = self.get_anomalies(100)
        surge = self.get_surge_items(20)
        symbols = set()
        for a in anomalies:
            sym = a.get("sym", "").replace("$", "")
            if sym: symbols.add(sym + "USDT")
        for s in surge:
            sym = s.get("sym", "")
            if sym: symbols.add(sym + "USDT")
        signals = []
        for sym in symbols:
            result = self.analyze_coin(sym)
            if abs(result["score"]) >= min_abs_score:
                signals.append(result)
        return sorted(signals, key=lambda x: -abs(x["score"]))

    def get_top_signals(self, limit=8):
        return self.get_coin_signals()[:limit]
