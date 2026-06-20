"""Hermes Daemon - startup script that wires MerCu data into HermesRunner.

This is the single entry point to run the trading system.
Replaces work/hermes-v2/daemon.py with the new event-driven architecture.

Usage:
  python -m app.services.hermes_strategies.hermes_daemon
  # or
  from app.services.hermes_strategies.hermes_daemon import run_hermes
  run_hermes()
"""
from __future__ import annotations
import sys
import os
import time
import signal
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from .event_bus import EventBus, Event, EventType
from .risk_engine import RiskEngine, RiskConfig
from .runner import HermesRunner, HealthReporter
from . import get_all_strategies, get_dag

BJT = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)


class MerCuDataBridge:
    """Bridges MerCu data (from hermes_mercu.py) into the EventBus + Runner."""

    def __init__(self):
        self._engine = None
        self._last_fetch_time: float = 0
        self._fetch_interval: int = 30  # seconds
        self._data_cache: Dict[str, Any] = {}
        self._fetch_errors: int = 0
        self._max_errors: int = 5

    @property
    def engine(self):
        """Lazy-load HermesSignalEngine from hermes_mercu."""
        if self._engine is None:
            try:
                from app.data_providers.hermes_mercu import get_hermes_engine
                self._engine = get_hermes_engine()
            except Exception as e:
                logger.error(f"Failed to load HermesSignalEngine: {e}")
                return None
        return self._engine

    def fetch(self) -> dict:
        """Fetch latest MerCu data. Returns dict with anomalies, momentum, etc."""
        now = time.time()
        if now - self._last_fetch_time < self._fetch_interval:
            return self._data_cache  # Use cached data

        try:
            engine = self.engine
            if engine is None:
                return {}

            data = {
                "anomalies": engine.get_anomalies(limit=100),
                "momentum": engine.get_momentum() if hasattr(engine, 'get_momentum') else {},
                "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")
            }

            self._data_cache = data
            self._last_fetch_time = now
            self._fetch_errors = 0

            # Emit to EventBus
            bus = EventBus.get()
            bus.emit(Event(EventType.MERCU_DATA, {
                "anomaly_count": len(data.get("anomalies", [])),
                "momentum_boards": len(data.get("momentum", {}).get("boards", {})),
                "timestamp": data["timestamp"]
            }, source="mercu_bridge"))

            return data

        except Exception as e:
            self._fetch_errors += 1
            logger.error(f"MerCu fetch error ({self._fetch_errors}/{self._max_errors}): {e}")
            bus = EventBus.get()
            bus.emit(Event(EventType.ERROR, {
                "component": "mercu_bridge",
                "error": str(e),
                "consecutive_errors": self._fetch_errors
            }, source="mercu_bridge"))

            if self._fetch_errors >= self._max_errors:
                bus.emit(Event(EventType.CIRCUIT_BREAKER, {
                    "reason": f"MerCu data fetch failed {self._fetch_errors} times consecutively",
                    "component": "mercu_bridge"
                }, source="mercu_bridge"))

            return self._data_cache  # Return stale cache rather than nothing

    def is_healthy(self) -> bool:
        """Check if data is fresh (fetched within 2x interval)."""
        return (time.time() - self._last_fetch_time) < (self._fetch_interval * 2)


def _setup_logging(log_dir: Optional[str] = None):
    """Configure logging to file + console."""
    log_dir = log_dir or os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "hermes_runner.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_hermes(
    risk_config: Optional[RiskConfig] = None,
    cycle_interval: int = 30,
    log_dir: Optional[str] = None
):
    """Main entry point: start the Hermes trading system.

    Args:
        risk_config: Custom risk parameters, or None for defaults.
        cycle_interval: Seconds between data fetch + strategy cycles.
        log_dir: Directory for log files.
    """
    _setup_logging(log_dir)

    logger.info("=" * 50)
    logger.info("Hermes V3 Starting - Event-Driven Architecture")
    logger.info("=" * 50)

    # 1. Reset singletons for clean start
    EventBus.reset()
    RiskEngine.reset()

    bus = EventBus.get()
    risk = RiskEngine.get(risk_config or RiskConfig())
    logger.info(f"RiskEngine: max_positions={risk.config.max_positions}, "
                f"daily_loss_limit={risk.config.max_daily_loss_pct*100}%, "
                f"drawdown_limit={risk.config.max_drawdown_pct*100}%")

    # 2. Create MerCu data bridge
    mercu = MerCuDataBridge()
    logger.info("MerCuDataBridge initialized")

    # 3. Create runner and load strategies
    runner = HermesRunner({"cycle_interval_seconds": cycle_interval})
    runner.load_from_registry()
    logger.info(f"Strategies loaded: {[s.name for s in runner._strategies]}")

    # 4. Start health reporter (background thread)
    health = HealthReporter(runner, interval_seconds=60)
    health.start()
    logger.info("HealthReporter started (60s interval)")

    # 5. Register signal handlers for graceful shutdown
    shutdown_event = threading.Event()

    def _shutdown(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        shutdown_event.set()
        runner.stop()
        health.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # 6. Run main loop
    logger.info(f"Starting main loop (cycle={cycle_interval}s)")
    logger.info("=" * 50)

    try:
        while not shutdown_event.is_set():
            cycle_start = time.time()

            try:
                # Fetch data
                mercu_data = mercu.fetch()

                if mercu_data:
                    # Run one cycle
                    runner._run_cycle(lambda: mercu_data)
                    runner._cycle_count += 1
                    runner.heartbeat("runner")
                else:
                    logger.warning("MerCu data empty, skipping cycle")

            except Exception as e:
                logger.error(f"Cycle error: {e}", exc_info=True)
                bus.emit(Event(EventType.ERROR, {
                    "component": "main_loop",
                    "error": str(e)
                }, source="main_loop"))

            # Sleep
            elapsed = time.time() - cycle_start
            sleep_time = max(0.5, cycle_interval - elapsed)
            if shutdown_event.wait(timeout=sleep_time):
                break

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")

    finally:
        runner.stop()
        health.stop()

        # Final status
        final = runner.get_health()
        logger.info(f"Shutdown complete. Cycles: {final['cycles']}, "
                     f"Signals: {final['signals']['generated']}gen/"
                     f"{final['signals']['approved']}approved/"
                     f"{final['signals']['blocked']}blocked")
        logger.info("=" * 50)


# ── Run directly ─────────────────────────────────────────────
if __name__ == "__main__":
    run_hermes()
