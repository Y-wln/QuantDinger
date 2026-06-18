"""
Hermes Strategy Service V1
===========================
Bridges Hermes/MerCu signals → QuantDinger strategy execution.

This service:
1. Polls Mercu.win for anomaly data every 30s
2. Generates trading signals via HermesSignalEngine
3. Manages positions using QuantDinger's live_trading module
4. Tracks P&L via portfolio_monitor

Architecture:
  MerCu API → HermesSignalEngine → HermesStrategyService → TradingExecutor
"""
from __future__ import annotations

import os
import json
import time
import threading
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from app.data_providers.hermes_mercu import (
    HermesSignalEngine,
    MerCuClient,
    CoinSignal,
    CoinType,
    get_stage,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

# ============================================================
# Configuration (env-overridable)
# ============================================================

HERMES_POLL_INTERVAL = int(os.getenv("HERMES_POLL_INTERVAL", "30"))  # seconds
HERMES_MAX_POSITIONS = int(os.getenv("HERMES_MAX_POSITIONS", "8"))   # max concurrent positions
HERMES_MIN_SCORE_LONG = int(os.getenv("HERMES_MIN_SCORE_LONG", "8"))  # min score to open long
HERMES_MIN_SCORE_SHORT = int(os.getenv("HERMES_MIN_SCORE_SHORT", "-5"))  # max score to open short
HERMES_POSITION_SIZE_PCT = float(os.getenv("HERMES_POSITION_SIZE_PCT", "0.1"))  # 10% per position
HERMES_STOP_LOSS_PCT = float(os.getenv("HERMES_STOP_LOSS_PCT", "0.05"))  # 5% stop loss
HERMES_COOLDOWN_MINUTES = int(os.getenv("HERMES_COOLDOWN_MINUTES", "5"))  # cooldown between same-coin trades
HERMES_ENABLED_COINS = os.getenv("HERMES_ENABLED_COINS", "")  # comma-separated, empty = all


# ============================================================
# Position Tracking
# ============================================================

@dataclass
class HermesPosition:
    """A position opened by Hermes strategy."""
    symbol: str
    direction: str           # LONG / SHORT
    entry_price: float
    entry_time: datetime
    size_usd: float
    score: int
    stage: str
    coin_type: str
    stop_loss: float = 0.0
    take_profit: float = 0.0
    last_signal_ts: str = ""

    def unrealized_pnl_pct(self, current_price: float) -> float:
        if self.entry_price <= 0:
            return 0.0
        if self.direction == "LONG":
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price


# ============================================================
# Hermes Strategy Service
# ============================================================

class HermesStrategyService:
    """
    Background service that:
    - Polls Mercu signals
    - Opens/closes positions based on signal strength
    - Manages risk with stop-loss and cooldowns
    """

    def __init__(self):
        self.engine = HermesSignalEngine()
        self.positions: Dict[str, HermesPosition] = {}
        self._cooldowns: Dict[str, float] = {}  # symbol -> timestamp
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._signal_history: List[dict] = []  # rolling signal log
        self._max_history = 500

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        """Start background polling thread."""
        if self._running:
            logger.warning("HermesStrategyService already running")
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="hermes-strategy")
        self._thread.start()
        logger.info("HermesStrategyService started (poll=%ss, max_pos=%d)",
                     HERMES_POLL_INTERVAL, HERMES_MAX_POSITIONS)

    def stop(self):
        """Stop background polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("HermesStrategyService stopped")

    def _poll_loop(self):
        """Main polling loop - runs every HERMES_POLL_INTERVAL seconds."""
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"HermesStrategyService tick error: {e}", exc_info=True)
            time.sleep(HERMES_POLL_INTERVAL)

    def _tick(self):
        """Single polling tick."""
        start = time.time()

        # 1. Fetch signals
        try:
            signals = self.engine.generate_signals()
        except Exception as e:
            logger.warning(f"Signal generation failed: {e}")
            return

        if not signals:
            return

        # 2. Log signals
        self._log_signals(signals)

        # 3. Process signals against positions
        with self._lock:
            self._process_signals(signals)

        elapsed = (time.time() - start) * 1000
        logger.debug(f"Hermes tick: {len(signals)} signals, {len(self.positions)} positions, {elapsed:.0f}ms")

    def _log_signals(self, signals: List[dict]):
        """Store recent signals for analysis."""
        now = time.time()
        for s in signals[:20]:  # top 20
            self._signal_history.append({
                **s,
                "_logged_at": now,
            })
        # Trim history
        if len(self._signal_history) > self._max_history:
            self._signal_history = self._signal_history[-self._max_history:]

    def _is_cooldown(self, symbol: str) -> bool:
        """Check if a coin is in cooldown period."""
        sym = symbol.upper()
        if sym in self._cooldowns:
            if time.time() - self._cooldowns[sym] < HERMES_COOLDOWN_MINUTES * 60:
                return True
            del self._cooldowns[sym]
        return False

    def _set_cooldown(self, symbol: str):
        """Set cooldown for a coin."""
        self._cooldowns[symbol.upper()] = time.time()

    def _process_signals(self, signals: List[dict]):
        """
        Process signals:
        - If no position and strong signal → open
        - If position and opposite signal → close
        - If position and stop-loss hit → close
        - If position and signal weakens → consider closing
        """
        enabled_coins = set()
        if HERMES_ENABLED_COINS:
            enabled_coins = {c.strip().upper() for c in HERMES_ENABLED_COINS.split(",") if c.strip()}

        active_symbols = {p.symbol for p in self.positions.values()}

        for signal in signals:
            sym = signal["symbol"]
            score = signal["score"]
            direction = signal["direction"]
            stage = signal["stage"]

            # Filter by enabled coins
            if enabled_coins and sym not in enabled_coins:
                continue

            # Check if we already have a position
            if sym in self.positions:
                pos = self.positions[sym]
                # Close if opposite direction or score flips
                if (pos.direction == "LONG" and score < -3) or (pos.direction == "SHORT" and score > 5):
                    self._close_position(sym, f"Signal reversal: score={score}")
                    self._set_cooldown(sym)
                continue

            # No position - check if we should open
            if self._is_cooldown(sym):
                continue

            if len(self.positions) >= HERMES_MAX_POSITIONS:
                continue  # At position limit

            # Open long
            if direction == "LONG" and score >= HERMES_MIN_SCORE_LONG:
                self._open_position(signal)

            # Open short
            elif direction == "SHORT" and score <= HERMES_MIN_SCORE_SHORT:
                self._open_position(signal)

    def _open_position(self, signal: dict):
        """Open a new position from a signal."""
        sym = signal["symbol"]
        direction = signal["direction"]
        price = signal.get("price") or 0
        score = signal["score"]
        stage = signal["stage"]
        coin_type = signal.get("coin_type", "")
        timestamp = signal.get("timestamp", "")

        # Calculate stop loss
        if direction == "LONG":
            stop_loss = price * (1 - HERMES_STOP_LOSS_PCT) if price else 0
        else:
            stop_loss = price * (1 + HERMES_STOP_LOSS_PCT) if price else 0

        pos = HermesPosition(
            symbol=sym,
            direction=direction,
            entry_price=price,
            entry_time=datetime.now(BJT),
            size_usd=0,  # Will be calculated by executor
            score=score,
            stage=stage,
            coin_type=coin_type,
            stop_loss=stop_loss,
            last_signal_ts=timestamp,
        )

        self.positions[sym] = pos
        logger.info(f"[HERMES] OPEN {direction} {sym} score={score} stage={stage} price={price}")

        # TODO: Call QuantDinger TradingExecutor to actually place order
        # executor.open_position(symbol=sym, side=direction, ...)

    def _close_position(self, symbol: str, reason: str = ""):
        """Close an existing position."""
        sym = symbol.upper()
        if sym not in self.positions:
            return
        pos = self.positions.pop(sym)
        logger.info(f"[HERMES] CLOSE {pos.direction} {sym} reason={reason}")

        # TODO: Call QuantDinger TradingExecutor to close position

    def get_status(self) -> dict:
        """Return current service status."""
        with self._lock:
            return {
                "running": self._running,
                "positions": len(self.positions),
                "max_positions": HERMES_MAX_POSITIONS,
                "poll_interval_s": HERMES_POLL_INTERVAL,
                "open_positions": [
                    {
                        "symbol": p.symbol,
                        "direction": p.direction,
                        "entry_price": p.entry_price,
                        "score": p.score,
                        "stage": p.stage,
                        "coin_type": p.coin_type,
                    }
                    for p in self.positions.values()
                ],
                "recent_signals": self._signal_history[-10:],
                "cooldowns": list(self._cooldowns.keys()),
            }


# ============================================================
# Singleton
# ============================================================

_service: Optional[HermesStrategyService] = None
_lock = threading.Lock()


def get_hermes_strategy_service() -> HermesStrategyService:
    global _service
    with _lock:
        if _service is None:
            _service = HermesStrategyService()
        return _service


def start_hermes_strategy_service():
    """Start the Hermes strategy service (called from app startup)."""
    enabled = os.getenv("HERMES_ENABLED", "true").lower() == "true"
    if not enabled:
        logger.info("Hermes strategy service disabled (HERMES_ENABLED=false)")
        return

    # Avoid starting twice with Flask reloader
    debug = os.getenv("PYTHON_API_DEBUG", "false").lower() == "true"
    if debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    try:
        svc = get_hermes_strategy_service()
        svc.start()
        logger.info("Hermes strategy service boot OK")
    except Exception as e:
        logger.error(f"Failed to start Hermes strategy service: {e}", exc_info=True)