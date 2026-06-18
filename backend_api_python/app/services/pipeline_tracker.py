"""
Pipeline Tracker V1 - 信号追踪引擎
====================================
QD-native signal lifecycle tracker.
Records every signal from generation through verification to close.

Tracks:
1. Signal generation time + source
2. Price at signal
3. Forward price at 5m/15m/1h/4h/24h
4. Whether signal was correct/incorrect
5. P&L if traded
"""
from __future__ import annotations

import os
import json
import time
import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

TRACKER_MAX_ENTRIES = int(os.getenv("TRACKER_MAX_ENTRIES", "5000"))
TRACKER_STORAGE_PATH = os.getenv("TRACKER_STORAGE_PATH", "pipeline_tracker.json")


@dataclass
class TrackedSignal:
    """A signal being tracked through its lifecycle."""
    id: str
    symbol: str
    source: str           # mercu / yaobi / lightning / ambush
    direction: str        # LONG / SHORT
    score: int
    signal_price: float
    signal_time: str
    stage: str = "generated"        # generated/verified/entered/closed
    forward_prices: Dict[str, float] = field(default_factory=dict)
    correct: Dict[str, bool] = field(default_factory=dict)
    pnl_pct: float = 0.0
    closed: bool = False
    close_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "source": self.source,
            "direction": self.direction,
            "score": self.score,
            "signal_price": self.signal_price,
            "signal_time": self.signal_time,
            "stage": self.stage,
            "forward_prices": self.forward_prices,
            "correct": self.correct,
            "pnl_pct": round(self.pnl_pct, 4),
            "closed": self.closed,
            "close_reason": self.close_reason,
        }


class PipelineTracker:
    """Tracks signals through their entire lifecycle."""

    HORIZONS = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "24h": 1440}

    def __init__(self):
        self._signals: Dict[str, TrackedSignal] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def track(self, signal_data: dict, source: str = "unknown") -> str:
        """Register a new signal for tracking. Returns signal ID."""
        with self._lock:
            self._counter += 1
            sid = f"{source[:3]}_{self._counter}_{int(time.time())}"

            ts = TrackedSignal(
                id=sid,
                symbol=signal_data.get("symbol", ""),
                source=source,
                direction=signal_data.get("direction", "NEUTRAL"),
                score=signal_data.get("score", 0),
                signal_price=signal_data.get("price", 0),
                signal_time=signal_data.get("timestamp", datetime.now(BJT).isoformat()),
                stage="generated",
            )

            self._signals[sid] = ts
            self._trim()
            return sid

    def update_forward(self, signal_id: str, horizon: str, price: float):
        """Record forward price at a horizon."""
        with self._lock:
            ts = self._signals.get(signal_id)
            if ts is None:
                return

            ts.forward_prices[horizon] = price
            if ts.signal_price > 0:
                pct = (price - ts.signal_price) / ts.signal_price
                if ts.direction == "SHORT":
                    pct = -pct
                ts.correct[horizon] = pct > 0

    def close_signal(self, signal_id: str, pnl_pct: float = 0.0, reason: str = ""):
        """Mark a signal as closed."""
        with self._lock:
            ts = self._signals.get(signal_id)
            if ts is None:
                return
            ts.closed = True
            ts.pnl_pct = pnl_pct
            ts.close_reason = reason
            ts.stage = "closed"

    def get_active(self) -> List[dict]:
        """Get active (unclosed) tracked signals."""
        with self._lock:
            return [s.to_dict() for s in self._signals.values() if not s.closed]

    def get_closed(self, limit: int = 50) -> List[dict]:
        """Get closed tracked signals."""
        with self._lock:
            closed = [s.to_dict() for s in self._signals.values() if s.closed]
            return closed[-limit:]

    def get_accuracy(self, horizon: str = "1h") -> dict:
        """Calculate accuracy for a given horizon."""
        with self._lock:
            closed = [s for s in self._signals.values() if s.closed and horizon in s.correct]
            if not closed:
                return {"accuracy": 0, "count": 0, "horizon": horizon}

            correct = sum(1 for s in closed if s.correct[horizon])
            return {
                "accuracy": round(correct / len(closed), 4),
                "count": len(closed),
                "horizon": horizon,
                "by_source": self._accuracy_by_source(closed, horizon),
            }

    def _accuracy_by_source(self, signals: list, horizon: str) -> dict:
        """Breakdown accuracy by signal source."""
        sources: Dict[str, dict] = {}
        for s in signals:
            src = s.source
            if src not in sources:
                sources[src] = {"total": 0, "correct": 0}
            sources[src]["total"] += 1
            if s.correct.get(horizon, False):
                sources[src]["correct"] += 1
        return {
            src: {
                "accuracy": round(v["correct"] / v["total"], 4),
                "count": v["total"],
            }
            for src, v in sources.items() if v["total"] > 0
        }

    def _trim(self):
        """Trim old entries if over max."""
        if len(self._signals) > TRACKER_MAX_ENTRIES:
            # Remove oldest closed signals
            closed = [(k, v) for k, v in self._signals.items() if v.closed]
            to_remove = len(self._signals) - TRACKER_MAX_ENTRIES
            for k, _ in sorted(closed, key=lambda x: x[1].signal_time)[:to_remove]:
                del self._signals[k]

    def get_status(self) -> dict:
        """Tracker status."""
        with self._lock:
            active = sum(1 for s in self._signals.values() if not s.closed)
            closed = sum(1 for s in self._signals.values() if s.closed)
            return {
                "total": len(self._signals),
                "active": active,
                "closed": closed,
                "accuracy_1h": self.get_accuracy("1h"),
                "accuracy_4h": self.get_accuracy("4h"),
            }

    def save(self):
        """Persist tracker state to disk."""
        try:
            with self._lock:
                data = {k: v.to_dict() for k, v in self._signals.items() if not v.closed}
            with open(TRACKER_STORAGE_PATH, "w") as f:
                json.dump({"signals": data, "counter": self._counter}, f)
        except Exception as e:
            logger.warning(f"Tracker save failed: {e}")

    def load(self):
        """Load tracker state from disk."""
        try:
            with open(TRACKER_STORAGE_PATH) as f:
                data = json.load(f)
            self._counter = data.get("counter", 0)
            logger.info(f"Tracker loaded: {len(data.get('signals', {}))} active signals")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Tracker load failed: {e}")


_tracker: Optional[PipelineTracker] = None


def get_pipeline_tracker() -> PipelineTracker:
    global _tracker
    if _tracker is None:
        _tracker = PipelineTracker()
        _tracker.load()
    return _tracker
