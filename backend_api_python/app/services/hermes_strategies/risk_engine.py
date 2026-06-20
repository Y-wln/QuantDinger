"""Risk Engine - position sizing, drawdown control, circuit breaker.

Standalone module. All trade decisions pass through here before execution.
Prevents: over-leverage, excessive loss, overtrading, runaway positions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import threading
import time as time_module

from .event_bus import EventBus, Event, EventType

BJT = timezone(timedelta(hours=8))


@dataclass
class RiskConfig:
    """All risk parameters in one place."""
    # Position limits
    max_positions: int = 8              # Max concurrent open positions
    max_per_symbol: int = 1             # Max positions per symbol
    max_position_pct: float = 0.15      # Max 15% of capital per position
    max_total_exposure_pct: float = 0.80 # Max 80% total capital exposed

    # Loss limits  
    max_daily_loss_pct: float = 0.05    # Stop trading if daily loss > 5%
    max_position_loss_pct: float = 0.03 # Hard stop per position at -3%
    max_consecutive_losses: int = 5     # Pause after N consecutive losses

    # Circuit breaker
    max_drawdown_pct: float = 0.12      # Full stop at 12% drawdown
    cooldown_minutes: int = 30          # Wait after circuit breaker trip

    # Signal quality
    min_score_long: int = 15            # Minimum score for long entry
    min_score_short: int = 15           # Minimum score for short entry
    max_slippage_pct: float = 0.005     # Max 0.5% slippage tolerance

    # Timing
    min_bars_between_trades: int = 3    # Don't trade every bar
    max_trades_per_hour: int = 10       # Rate limit


@dataclass  
class RiskVerdict:
    """Result of risk check."""
    approved: bool
    reason: str = ""
    adjusted_size_pct: float = 0.0
    warnings: List[str] = field(default_factory=list)


class CircuitBreaker:
    """Trips on conditions and requires cooldown before reset."""

    def __init__(self, max_drawdown_pct: float = 0.12, cooldown_minutes: int = 30):
        self.max_drawdown_pct = max_drawdown_pct
        self.cooldown_seconds = cooldown_minutes * 60
        self.tripped_at: Optional[float] = None
        self.trip_reason: str = ""
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        """True = breaker tripped, trading blocked."""
        if self.tripped_at is None:
            return False
        if time_module.time() - self.tripped_at > self.cooldown_seconds:
            with self._lock:
                self.tripped_at = None
                self.trip_reason = ""
            return False
        return True

    def trip(self, reason: str):
        """Trip the breaker."""
        with self._lock:
            self.tripped_at = time_module.time()
            self.trip_reason = reason
        bus = EventBus.get()
        bus.emit(Event(EventType.CIRCUIT_BREAKER, {
            "reason": reason,
            "cooldown_minutes": self.cooldown_seconds // 60
        }, source="risk_engine"))

    def remaining_cooldown_seconds(self) -> int:
        """Seconds until breaker resets."""
        if self.tripped_at is None:
            return 0
        elapsed = time_module.time() - self.tripped_at
        return max(0, int(self.cooldown_seconds - elapsed))


class RiskEngine:
    """Central risk controller. Singleton per process."""

    _instance: Optional["RiskEngine"] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.breaker = CircuitBreaker(
            max_drawdown_pct=self.config.max_drawdown_pct,
            cooldown_minutes=self.config.cooldown_minutes
        )
        self._positions: Dict[str, Dict] = {}       # symbol -> position info
        self._trade_history: List[Dict] = []         # Recent trades
        self._daily_pnl: float = 0.0
        self._consecutive_losses: int = 0
        self._trade_count_hour: int = 0
        self._hour_start: float = time_module.time()
        self._data_lock = threading.Lock()

    @classmethod
    def get(cls, config: Optional[RiskConfig] = None) -> "RiskEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = RiskEngine(config)
        return cls._instance

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._instance = None

    # ── Position tracking ──────────────────────────────────────

    def update_position(self, symbol: str, side: str, size_pct: float, 
                        entry_price: float, current_price: float):
        """Register or update a position."""
        with self._data_lock:
            pnl_pct = 0.0
            if side.upper() == "LONG":
                pnl_pct = ((current_price - entry_price) / entry_price) * size_pct
            elif side.upper() == "SHORT":
                pnl_pct = ((entry_price - current_price) / entry_price) * size_pct

            self._positions[symbol] = {
                "side": side, "size_pct": size_pct,
                "entry_price": entry_price, "current_price": current_price,
                "pnl_pct": pnl_pct
            }

    def close_position(self, symbol: str, exit_price: float):
        """Remove position and record PnL."""
        with self._data_lock:
            pos = self._positions.pop(symbol, None)
            if pos:
                if pos["side"].upper() == "LONG":
                    pnl = ((exit_price - pos["entry_price"]) / pos["entry_price"]) * pos["size_pct"]
                else:
                    pnl = ((pos["entry_price"] - exit_price) / pos["entry_price"]) * pos["size_pct"]
                self._daily_pnl += pnl
                self._trade_history.append({
                    "symbol": symbol, "side": pos["side"],
                    "entry": pos["entry_price"], "exit": exit_price,
                    "pnl_pct": pnl, "time": datetime.now(BJT).isoformat()
                })
                if pnl < 0:
                    self._consecutive_losses += 1
                else:
                    self._consecutive_losses = 0

    @property
    def open_positions_count(self) -> int:
        return len(self._positions)

    @property
    def total_exposure_pct(self) -> float:
        return sum(p["size_pct"] for p in self._positions.values())

    # ── Risk checks ─────────────────────────────────────────────

    def check_signal(self, symbol: str, direction: str, score: int,
                     price: float, size_pct: Optional[float] = None) -> RiskVerdict:
        """Full risk check before a trade. Returns verdict."""
        warnings = []

        # 1. Circuit breaker
        if self.breaker.is_open:
            return RiskVerdict(False, 
                f"断路器熔断: {self.breaker.trip_reason} "
                f"(剩余{self.breaker.remaining_cooldown_seconds()}秒)",
                warnings=["🛑 断路器开启"])

        # 2. Max positions
        if self.open_positions_count >= self.config.max_positions:
            return RiskVerdict(False,
                f"持仓已满 ({self.open_positions_count}/{self.config.max_positions})",
                warnings=["⚠️ 满仓"])

        # 3. Per-symbol limit
        if symbol in self._positions:
            return RiskVerdict(False,
                f"{symbol} 已有持仓",
                warnings=[f"⚠️ {symbol}重复"])

        # 4. Score threshold
        min_score = self.config.min_score_long if direction.upper() == "LONG" else self.config.min_score_short
        if abs(score) < min_score:
            return RiskVerdict(False,
                f"评分不足 ({abs(score)} < {min_score})",
                warnings=[f"📉 评分{abs(score)}<{min_score}"])

        # 5. Daily loss limit
        if self._daily_pnl <= -self.config.max_daily_loss_pct:
            self.breaker.trip(f"日内亏损达到{self.config.max_daily_loss_pct*100}%")
            return RiskVerdict(False,
                f"日内亏损超限 ({self._daily_pnl*100:.1f}%)",
                warnings=["🛑 日内止损"])

        # 6. Consecutive losses
        if self._consecutive_losses >= self.config.max_consecutive_losses:
            return RiskVerdict(False,
                f"连续亏损{self._consecutive_losses}次，暂停",
                warnings=["🛑 连亏暂停"])

        # 7. Exposure limit
        actual_size = size_pct or self.config.max_position_pct
        if self.total_exposure_pct + actual_size > self.config.max_total_exposure_pct:
            actual_size = max(0, self.config.max_total_exposure_pct - self.total_exposure_pct)
            if actual_size < 0.03:
                return RiskVerdict(False,
                    f"总敞口已达上限 ({self.total_exposure_pct*100:.0f}%)",
                    warnings=["⚠️ 敞口上限"])
            warnings.append(f"📐 仓位调整为{actual_size*100:.1f}%")

        # 8. Rate limit
        now = time_module.time()
        if now - self._hour_start > 3600:
            self._trade_count_hour = 0
            self._hour_start = now
        if self._trade_count_hour >= self.config.max_trades_per_hour:
            return RiskVerdict(False,
                f"每小时交易次数超限 ({self.config.max_trades_per_hour})",
                warnings=["⏱️ 频率限制"])

        # Approved
        return RiskVerdict(True, "通过", adjusted_size_pct=actual_size, warnings=warnings)

    def record_trade_attempt(self):
        """Call after check_signal passes and order is placed."""
        with self._data_lock:
            self._trade_count_hour += 1

    def check_drawdown(self, peak_capital: float, current_capital: float) -> bool:
        """Check if drawdown exceeds threshold. Returns True if OK."""
        if peak_capital <= 0:
            return True
        dd = (peak_capital - current_capital) / peak_capital
        if dd >= self.config.max_drawdown_pct:
            self.breaker.trip(f"回撤达到{dd*100:.1f}% (峰值{peak_capital:.1f} → 当前{current_capital:.1f})")
            return False
        return True

    def get_status(self) -> dict:
        """Full risk status snapshot."""
        return {
            "breaker_open": self.breaker.is_open,
            "breaker_reason": self.breaker.trip_reason,
            "cooldown_remaining_s": self.breaker.remaining_cooldown_seconds(),
            "open_positions": self.open_positions_count,
            "max_positions": self.config.max_positions,
            "total_exposure_pct": round(self.total_exposure_pct * 100, 1),
            "daily_pnl_pct": round(self._daily_pnl * 100, 2),
            "consecutive_losses": self._consecutive_losses,
            "trades_this_hour": self._trade_count_hour,
            "positions_detail": {
                sym: {
                    "side": p["side"], "size_pct": round(p["size_pct"]*100, 1),
                    "pnl_pct": round(p["pnl_pct"]*100, 2),
                    "entry": p["entry_price"]
                } for sym, p in self._positions.items()
            }
        }
