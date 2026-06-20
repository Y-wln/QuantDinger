"""Position Manager V3 - thread-safe position state tracking.

Replaces hermes_strategy_service.py's HermesPosition + position management.
Connects to EventBus for trade signals and RiskEngine for approval.
"""
from __future__ import annotations
import time
import threading
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

BJT = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """A tracked position with P&L calculation."""
    symbol: str
    direction: str           # LONG / SHORT
    entry_price: float
    entry_time: datetime
    size_usd: float = 0.0
    score: int = 0
    stage: str = ""
    coin_type: str = ""
    stop_loss: float = 0.0
    take_profit: float = 0.0
    last_signal_ts: str = ""
    order_id: str = ""
    
    def unrealized_pnl_pct(self, current_price: float) -> float:
        if self.entry_price <= 0 or current_price <= 0:
            return 0.0
        if self.direction == "LONG":
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "size_usd": self.size_usd,
            "score": self.score,
            "stage": self.stage,
            "coin_type": self.coin_type,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "order_id": self.order_id,
        }


class PositionManager:
    """Thread-safe position tracker with cooldown management.
    
    Singleton pattern - use PositionManager.get() to access.
    Connects to EventBus to emit position open/close events.
    """
    _instance: Optional[PositionManager] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self._cooldowns: Dict[str, float] = {}
        self._cooldown_seconds: int = 300  # 5 min default
        self._max_positions: int = 8
        self._min_score_long: int = 8
        self._min_score_short: int = -5
        self._mutex = threading.Lock()
        self._history: List[dict] = []
        self._max_history: int = 500
    
    @classmethod
    def get(cls) -> PositionManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        with cls._lock:
            cls._instance = None
    
    # ── Configuration ──────────────────────────────
    
    def configure(self, max_positions: int = 8, min_score_long: int = 8,
                  min_score_short: int = -5, cooldown_seconds: int = 300):
        self._max_positions = max_positions
        self._min_score_long = min_score_long
        self._min_score_short = min_score_short
        self._cooldown_seconds = cooldown_seconds
    
    # ── Position CRUD ──────────────────────────────
    
    def open(self, position: Position) -> bool:
        """Open a new position. Returns False if at limit."""
        with self._mutex:
            sym = position.symbol.upper()
            if sym in self.positions:
                logger.warning(f"Position already exists for {sym}")
                return False
            if len(self.positions) >= self._max_positions:
                logger.warning(f"Position limit reached ({self._max_positions})")
                return False
            self.positions[sym] = position
            self._add_history("open", position.to_dict())
            self._set_cooldown(sym)
            logger.info(f"[PM] OPEN {position.direction} {sym} @ {position.entry_price} score={position.score}")
            self._emit_event("position_opened", position.to_dict())
            return True
    
    def close(self, symbol: str, reason: str = "", current_price: float = 0) -> Optional[Position]:
        """Close a position. Returns the closed position or None."""
        with self._mutex:
            sym = symbol.upper()
            if sym not in self.positions:
                return None
            pos = self.positions.pop(sym)
            pnl = pos.unrealized_pnl_pct(current_price) if current_price else 0
            info = pos.to_dict()
            info["close_reason"] = reason
            info["close_price"] = current_price
            info["pnl_pct"] = round(pnl * 100, 2)
            self._add_history("close", info)
            logger.info(f"[PM] CLOSE {pos.direction} {sym} reason={reason} pnl={pnl*100:.2f}%")
            self._emit_event("position_closed", info)
            return pos
    
    def get_position(self, symbol: str) -> Optional[Position]:
        sym = symbol.upper()
        with self._mutex:
            return self.positions.get(sym)
    
    def get_all(self) -> List[Position]:
        with self._mutex:
            return list(self.positions.values())
    
    def get_count(self) -> int:
        with self._mutex:
            return len(self.positions)
    
    def update_price(self, symbol: str, current_price: float):
        """Update P&L for a position without changing entry."""
        # P&L is calculated on the fly via unrealized_pnl_pct()
        pass
    
    # ── Cooldown ───────────────────────────────────
    
    def is_cooldown(self, symbol: str) -> bool:
        sym = symbol.upper()
        with self._mutex:
            if sym in self._cooldowns:
                if time.time() - self._cooldowns[sym] < self._cooldown_seconds:
                    return True
                del self._cooldowns[sym]
        return False
    
    def _set_cooldown(self, symbol: str):
        self._cooldowns[symbol.upper()] = time.time()
    
    # ── Signal Evaluation ──────────────────────────
    
    def can_open_long(self, symbol: str, score: int) -> bool:
        """Check if we can open a long position for this signal."""
        sym = symbol.upper()
        with self._mutex:
            if sym in self.positions:
                return False
            if self.is_cooldown(sym):
                return False
            if len(self.positions) >= self._max_positions:
                return False
            if score < self._min_score_long:
                return False
        return True
    
    def can_open_short(self, symbol: str, score: int) -> bool:
        """Check if we can open a short position for this signal."""
        sym = symbol.upper()
        with self._mutex:
            if sym in self.positions:
                return False
            if self.is_cooldown(sym):
                return False
            if len(self.positions) >= self._max_positions:
                return False
            if score > self._min_score_short:
                return False
        return True
    
    def should_close(self, symbol: str, direction: str, new_score: int) -> bool:
        """Check if an existing position should be closed based on new signal."""
        sym = symbol.upper()
        with self._mutex:
            if sym not in self.positions:
                return False
            pos = self.positions[sym]
            if pos.direction == "LONG" and new_score < -3:
                return True
            if pos.direction == "SHORT" and new_score > 5:
                return True
        return False
    
    # ── History + Events ───────────────────────────
    
    def _add_history(self, action: str, data: dict):
        entry = {"action": action, "time": time.time(), **data}
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def _emit_event(self, event_type: str, data: dict):
        try:
            from .event_bus import EventBus, Event, EventType
            bus = EventBus.get()
            etype = EventType.POSITION_OPENED if "opened" in event_type else EventType.POSITION_CLOSED
            bus.emit(Event(type=etype, data=data, source="position_manager"))
        except Exception:
            pass
    
    def get_history(self, limit: int = 50) -> List[dict]:
        with self._mutex:
            return list(reversed(self._history[-limit:]))
    
    def get_status(self) -> dict:
        with self._mutex:
            longs = sum(1 for p in self.positions.values() if p.direction == "LONG")
            shorts = sum(1 for p in self.positions.values() if p.direction == "SHORT")
            return {
                "active_positions": len(self.positions),
                "max_positions": self._max_positions,
                "long_positions": longs,
                "short_positions": shorts,
                "positions": [p.to_dict() for p in self.positions.values()],
                "cooldowns": list(self._cooldowns.keys()),
                "cooldown_seconds": self._cooldown_seconds,
            }
    
    def get_dashboard_metrics(self) -> dict:
        """Metrics for QD dashboard."""
        status = self.get_status()
        history = self.get_history(50)
        closed = [h for h in history if h["action"] == "close"]
        avg_pnl = sum(abs(h.get("pnl_pct", 0)) for h in closed) / max(len(closed), 1) if closed else 0
        return {
            "active_positions": status["active_positions"],
            "max_positions": status["max_positions"],
            "long_positions": status["long_positions"],
            "short_positions": status["short_positions"],
            "positions": status["positions"],
            "recent_closes": len(closed),
            "avg_closed_pnl_pct": round(avg_pnl, 2),
        }

