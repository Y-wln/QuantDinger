"""MerCu data bridge V2 - reads real-time data from mercu_headless.py poller."""
import json, os, time, glob

DATA_DIR = "/home/ubuntu/scripts/agents/mercu_data"

class MerCuBridge:
    """Reads MerCu data files polled by mercu_headless.py."""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

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
        """Check if anomaly data is fresh."""
        fpath = os.path.join(self.data_dir, "anomaly-v4_100.json")
        if not os.path.exists(fpath):
            return False
        return (time.time() - os.path.getmtime(fpath)) < max_age

    def get_anomalies(self, limit=20):
        """Get recent anomaly events (OI surge, volume burst, etc.)."""
        data = self._read_file("anomaly-v4_100.json")
        items = data.get("data", [])
        return items[:limit]

    def get_surge(self, limit=10):
        """Get volume surge items."""
        data = self._read_file("surge_5.json")
        items = data.get("items", [])
        return items[:limit]

    def get_momentum(self):
        """Get 15m momentum rankings."""
        return self._read_file("momentum_15m.json")

    def get_rank(self):
        """Get hot ranking."""
        return self._read_file("rank.json")

    def get_plaza(self):
        """Get plaza sentiment data."""
        return self._read_file("plaza.json")

    def get_oi_signal(self, symbol):
        """Extract OI flow signal for a symbol from anomalies."""
        sym_clean = symbol.replace("USDT", "")
        anomalies = self.get_anomalies(100)
        oi_events = []
        for a in anomalies:
            if a.get("sym", "").replace("$", "") == sym_clean and a.get("main_dim") == "oi":
                oi_events.append({
                    "direction": "up" if a.get("main_direction") == 1 else "down",
                    "amount": a.get("main_amount", 0),
                    "window": a.get("main_window", "?"),
                    "grade": a.get("grade", "?"),
                    "sentence": a.get("l1_sentence", ""),
                })
        return oi_events

    def get_coin_signals(self):
        """Generate trading signals from MerCu anomaly + surge data."""
        signals = []
        anomalies = self.get_anomalies(100)
        surge_items = self.get_surge(20)
        surge_syms = {s["sym"] for s in surge_items}

        for a in anomalies:
            sym = a.get("sym", "").replace("$", "")
            if not sym:
                continue
            dim = a.get("main_dim", "")
            direction = a.get("main_direction", 0)
            grade = a.get("grade", "")
            percentile = a.get("percentile", 0)
            surge_bonus = sym in surge_syms

            score = 0
            reasons = []

            # Score OI surge
            if dim == "oi" and percentile > 0.95:
                score += 5 if grade == "SS" else 3
                reasons.append(f"OI{'+' if direction>0 else '-'}{a.get('main_amount',0):.1f}")

            # Score volume burst
            if dim == "vol" and percentile > 0.9:
                score += 3
                reasons.append(f"Vol{a.get('main_value',0):.1f}x")

            # Surge bonus
            if surge_bonus:
                score += 2
                reasons.append("Surge??")

            if score >= 5:
                signals.append({
                    "symbol": sym + "USDT",
                    "direction": "long" if direction > 0 else "short",
                    "score": score,
                    "reasons": reasons,
                    "grade": grade,
                    "percentile": percentile,
                })

        return sorted(signals, key=lambda x: -x["score"])
