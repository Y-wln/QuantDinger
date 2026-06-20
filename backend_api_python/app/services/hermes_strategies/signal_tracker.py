"""Signal Tracker - full lifecycle tracking from signal to outcome.

Records every signal, tracks price after entry, computes win rate,
identifies which indicators correlate with profitable trades.

Architecture:
  EventBus → SignalTracker (capture) → PriceTracker (follow) → AccuracyAnalyzer (report)
  
All three layers work together to answer:
  1. Did the signal lead to profit?
  2. Which indicators predicted correctly?
  3. What's the real accuracy per strategy/coin/timeframe?
"""
from __future__ import annotations
import json
import os
import time
import threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .event_bus import EventBus, Event, EventType, on

BJT = timezone(timedelta(hours=8))

# ── Data structures ──────────────────────────────────────────

@dataclass
class TrackedSignal:
    """One tracked signal with full lifecycle data."""
    id: str
    symbol: str
    direction: str       # LONG / SHORT
    score: int
    entry_price: float
    entry_time: str
    source: str          # strategy name
    reasons: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    
    # Price tracking (populated over time)
    price_snapshots: Dict[str, float] = field(default_factory=dict)  # "5m": 100.5, "15m": 101.2, ...
    exit_price: float = 0.0
    exit_time: str = ""
    
    # Outcome
    outcome: str = "open"  # open / win / loss / breakeven
    pnl_pct: float = 0.0
    max_favorable_pct: float = 0.0
    max_adverse_pct: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id, "symbol": self.symbol, "direction": self.direction,
            "score": self.score, "entry_price": self.entry_price,
            "entry_time": self.entry_time, "source": self.source,
            "reasons": self.reasons, "indicators": self.indicators,
            "price_snapshots": self.price_snapshots,
            "exit_price": self.exit_price, "exit_time": self.exit_time,
            "outcome": self.outcome, "pnl_pct": round(self.pnl_pct, 4),
            "max_favorable_pct": round(self.max_favorable_pct, 4),
            "max_adverse_pct": round(self.max_adverse_pct, 4),
        }


class PriceTracker:
    """Tracks prices for open signals. In production, this uses live kline data.
    For testing, it can use Mercu momentum data or cached prices."""

    def __init__(self):
        self._prices: Dict[str, float] = {}  # symbol -> latest price
        self._history: Dict[str, List[Tuple[float, float]]] = defaultdict(list)  # symbol -> [(ts, price)]
        self._lock = threading.Lock()

    def update_price(self, symbol: str, price: float):
        """Called on each new price tick."""
        with self._lock:
            self._prices[symbol] = price
            self._history[symbol].append((time.time(), price))
            # Keep last 24h of 1m candles
            if len(self._history[symbol]) > 1440:
                self._history[symbol] = self._history[symbol][-1440:]

    def get_price(self, symbol: str) -> float:
        with self._lock:
            return self._prices.get(symbol, 0.0)

    def get_price_at(self, symbol: str, seconds_ago: float) -> Optional[float]:
        """Get approximate price at a point in the past."""
        with self._lock:
            hist = self._history.get(symbol, [])
            if not hist:
                return None
            target = time.time() - seconds_ago
            # Find closest price to target time
            closest = min(hist, key=lambda x: abs(x[0] - target))
            return closest[1]

    def update_from_mercu(self, mercu_data: dict):
        """Update prices from MerCu momentum board data."""
        momentum = mercu_data.get("momentum", {})
        boards = momentum.get("boards", {})
        for side in ("priceUp", "priceDown"):
            for item in boards.get(side, []):
                sym = item.get("sym", "")
                val_str = item.get("val", "0%")
                try:
                    pct = float(val_str.replace("%", "").replace("+", ""))
                    if self._prices.get(sym):
                        # We know current price and % change
                        pass  # Need base price from exchange
                except ValueError:
                    pass


class SignalTracker:
    """Core tracking engine. Subscribes to EventBus, tracks all signals end-to-end."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "logs", "tracker"
        )
        os.makedirs(self.storage_dir, exist_ok=True)

        self._signals: Dict[str, TrackedSignal] = {}  # id -> signal
        self._price_tracker = PriceTracker()
        self._lock = threading.Lock()
        self._signal_counter: int = 0

        # Auto-subscribe to events
        bus = EventBus.get()
        bus.subscribe(EventType.SIGNAL_GENERATED, self._on_signal)
        bus.subscribe(EventType.ORDER_FILLED, self._on_fill)
        bus.subscribe(EventType.MARKET_DATA, self._on_price)

    # ── Event handlers ──────────────────────────────────────

    def _on_signal(self, event: Event):
        """Captures every generated signal."""
        data = event.data
        symbol = data.get("symbol", "?")
        direction = data.get("direction", "NEUTRAL")
        if direction == "NEUTRAL":
            return

        self._signal_counter += 1
        sig_id = f"{symbol}_{self._signal_counter}_{int(time.time())}"

        tracked = TrackedSignal(
            id=sig_id,
            symbol=symbol,
            direction=direction,
            score=data.get("score", 0),
            entry_price=data.get("price", 0.0),
            entry_time=event.timestamp,
            source=data.get("source", "unknown"),
            reasons=data.get("reasons", []),
            indicators=self._extract_indicators(data.get("reasons", []))
        )

        with self._lock:
            self._signals[sig_id] = tracked

    def _on_fill(self, event: Event):
        """Records when an order is filled (trade actually entered)."""
        data = event.data
        symbol = data.get("symbol", "")
        price = data.get("price", 0.0)
        # Update the latest signal for this symbol
        with self._lock:
            for sig in reversed(list(self._signals.values())):
                if sig.symbol == symbol and sig.outcome == "open":
                    sig.entry_price = price
                    break

    def _on_price(self, event: Event):
        """Updates price tracker on new market data."""
        data = event.data
        symbol = data.get("symbol", "")
        price = data.get("price", 0.0)
        if symbol and price:
            self._price_tracker.update_price(symbol, price)

    def _extract_indicators(self, reasons: List[str]) -> List[str]:
        """Extract indicator names from signal reasons."""
        indicators = []
        keywords = {
            "OI": "oi", "CVD": "cvd", "RSI": "rsi", "MACD": "macd",
            "BB": "bb", "SMC": "smc", "MA": "ma", "volume": "volume",
            "orderbook": "orderbook", "liquidation": "liquidation",
            "Plaza": "plaza", "Perp": "perp", "Spot": "spot",
            "吸筹": "accumulation", "派发": "distribution",
            "多头": "bullish", "空头": "bearish", "共振": "resonance",
            "Vol": "volume_surge", "tape": "tape",
        }
        for reason in reasons:
            for key, val in keywords.items():
                if key.lower() in reason.lower() and val not in indicators:
                    indicators.append(val)
        return indicators

    # ── Price snapshotting ──────────────────────────────────

    def take_snapshots(self):
        """Record current prices for all open signals."""
        intervals = [300, 900, 3600, 14400]  # 5m, 15m, 1h, 4h in seconds
        interval_labels = ["5m", "15m", "1h", "4h"]

        with self._lock:
            for sig_id, sig in list(self._signals.items()):
                if sig.outcome != "open":
                    continue
                if not sig.entry_price:
                    continue

                current_price = self._price_tracker.get_price(sig.symbol)
                if not current_price:
                    continue

                # Calculate elapsed time
                try:
                    entry_dt = datetime.strptime(sig.entry_time, "%Y-%m-%d %H:%M:%S")
                    entry_dt = entry_dt.replace(tzinfo=BJT)
                    elapsed = (datetime.now(BJT) - entry_dt).total_seconds()
                except (ValueError, TypeError):
                    elapsed = 0

                # Take snapshot for each interval that has passed
                for label, interval in zip(interval_labels, intervals):
                    if elapsed >= interval and label not in sig.price_snapshots:
                        # Get historical price (approximate)
                        past_price = self._price_tracker.get_price_at(
                            sig.symbol, elapsed - interval
                        )
                        if past_price:
                            sig.price_snapshots[label] = past_price

                # Update MFE/MAE
                if current_price and sig.entry_price > 0:
                    if sig.direction == "LONG":
                        change = (current_price - sig.entry_price) / sig.entry_price
                    else:
                        change = (sig.entry_price - current_price) / sig.entry_price
                    sig.max_favorable_pct = max(sig.max_favorable_pct, change)
                    sig.max_adverse_pct = min(sig.max_adverse_pct, change)

    # ── Close signals ───────────────────────────────────────

    def close_signal(self, sig_id: str, exit_price: float, exit_time: Optional[str] = None):
        """Mark a signal as closed. Handles zero entry prices gracefully."""
        """Mark a signal as closed with exit price."""
        with self._lock:
            sig = self._signals.get(sig_id)
            if not sig:
                return

            sig.exit_price = exit_price
            sig.exit_time = exit_time or datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

            if sig.entry_price > 0:
                if sig.direction == "LONG":
                    sig.pnl_pct = (exit_price - sig.entry_price) / sig.entry_price
                else:
                    sig.pnl_pct = (sig.entry_price - exit_price) / sig.entry_price
            else:
                sig.pnl_pct = 0.0  # No entry price available

            if sig.pnl_pct > 0.003:  # > 0.3% profit
                sig.outcome = "win"
            elif sig.pnl_pct < -0.003:  # < -0.3% loss
                sig.outcome = "loss"
            else:
                sig.outcome = "breakeven"

    def close_all_at_price(self, symbol: str, current_price: float):
        """Close all open signals for a symbol at current price."""
        with self._lock:
            for sig_id, sig in list(self._signals.items()):
                if sig.symbol == symbol and sig.outcome == "open":
                    self.close_signal(sig_id, current_price)

    # ── Statistics ──────────────────────────────────────────

    def get_stats(self) -> dict:
        """Comprehensive accuracy statistics."""
        with self._lock:
            all_sigs = list(self._signals.values())
            closed = [s for s in all_sigs if s.outcome != "open"]
            open_sigs = [s for s in all_sigs if s.outcome == "open"]
            wins = [s for s in closed if s.outcome == "win"]
            losses = [s for s in closed if s.outcome == "loss"]

            # Overall stats
            total = len(closed)
            win_count = len(wins)
            win_rate = win_count / max(1, total)

            # Per-source stats
            by_source = defaultdict(lambda: {"total": 0, "wins": 0, "pnl_sum": 0.0})
            for s in closed:
                src = s.source
                by_source[src]["total"] += 1
                if s.outcome == "win":
                    by_source[src]["wins"] += 1
                by_source[src]["pnl_sum"] += s.pnl_pct

            source_stats = {}
            for src, data in by_source.items():
                source_stats[src] = {
                    "total": data["total"],
                    "wins": data["wins"],
                    "win_rate": round(data["wins"] / max(1, data["total"]) * 100, 1),
                    "avg_pnl_pct": round(data["pnl_sum"] / max(1, data["total"]) * 100, 2),
                    "total_pnl_pct": round(data["pnl_sum"] * 100, 2),
                }

            # Per-indicator stats
            by_indicator = defaultdict(lambda: {"signals": 0, "wins": 0})
            for s in all_sigs:
                for ind in s.indicators:
                    by_indicator[ind]["signals"] += 1
                    if s.outcome == "win":
                        by_indicator[ind]["wins"] += 1

            indicator_stats = {}
            for ind, data in sorted(by_indicator.items(), key=lambda x: -x[1]["signals"]):
                if data["signals"] >= 3:  # Minimum sample size
                    indicator_stats[ind] = {
                        "signals": data["signals"],
                        "win_rate": round(data["wins"] / max(1, data["signals"]) * 100, 1),
                    }

            # Per-coin stats
            by_coin = defaultdict(lambda: {"total": 0, "wins": 0})
            for s in closed:
                by_coin[s.symbol]["total"] += 1
                if s.outcome == "win":
                    by_coin[s.symbol]["wins"] += 1

            coin_stats = {}
            for coin, data in sorted(by_coin.items(), key=lambda x: -x[1]["total"]):
                coin_stats[coin] = {
                    "total": data["total"],
                    "win_rate": round(data["wins"] / max(1, data["total"]) * 100, 1),
                }

            return {
                "total_signals": len(all_sigs),
                "open": len(open_sigs),
                "closed": total,
                "wins": win_count,
                "losses": len(losses),
                "breakeven": total - win_count - len(losses),
                "win_rate": round(win_rate * 100, 1),
                "avg_pnl_pct": round(
                    sum(s.pnl_pct for s in closed) / max(1, total) * 100, 2
                ),
                "total_pnl_pct": round(sum(s.pnl_pct for s in closed) * 100, 2),
                "by_source": source_stats,
                "by_indicator": indicator_stats,
                "by_coin": coin_stats,
            }

    def get_recent(self, limit: int = 50) -> List[dict]:
        """Get recent signals as dicts."""
        with self._lock:
            sigs = list(self._signals.values())[-limit:]
            return [s.to_dict() for s in sigs]

    def save(self):
        """Persist tracker state to disk."""
        filepath = os.path.join(self.storage_dir, "tracker_state.json")
        with self._lock:
            data = {
                "updated": datetime.now(BJT).isoformat(),
                "stats": self.get_stats(),
                "recent": self.get_recent(20),
                "total_tracked": len(self._signals),
            }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        """Load previous tracker state."""
        filepath = os.path.join(self.storage_dir, "tracker_state.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None


# ── Metrics reporter (periodic) ─────────────────────────────

class TrackerReporter:
    """Periodically saves tracker state and logs summary metrics."""

    def __init__(self, tracker: SignalTracker, interval_seconds: int = 60):
        self.tracker = tracker
        self.interval = interval_seconds
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            time.sleep(self.interval)
            try:
                self.tracker.take_snapshots()
                self.tracker.save()
                stats = self.tracker.get_stats()
                bus = EventBus.get()
                bus.emit(Event(EventType.HEARTBEAT, {
                    "component": "tracker",
                    "tracked": stats["total_signals"],
                    "win_rate": stats["win_rate"],
                    "open": stats["open"],
                }, source="tracker"))
            except Exception:
                pass


# ── Singleton ───────────────────────────────────────────────

_tracker_instance: Optional[SignalTracker] = None


def get_tracker(storage_dir: Optional[str] = None) -> SignalTracker:
    """Get or create the global SignalTracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = SignalTracker(storage_dir)
    return _tracker_instance


