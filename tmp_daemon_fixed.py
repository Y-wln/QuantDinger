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
    """Bridges ALL MerCu data (9 endpoints) into the EventBus + Runner.
    
    V3 Extended: fetches all V2 endpoints (anomalies, momentum, surge, rank, 
    plaza, deep, briefs, dashboard) plus computed indicators.
    """

    def __init__(self):
        self._engine = None
        self._last_fetch_time: float = 0
        self._fetch_interval: int = 30  # seconds
        self._data_cache: Dict[str, Any] = {}
        self._fetch_errors: int = 0
        self._max_errors: int = 5

    @property
    def engine(self):
        """Lazy-load HermesSignalEngine from hermes_mercu with retry on failure."""
        if self._engine is None:
            try:
                from app.data_providers.hermes_mercu import get_hermes_engine
                self._engine = get_hermes_engine()
                logger.info("HermesSignalEngine loaded")
            except Exception as e:
                logger.warning(f"Failed to load HermesSignalEngine (will retry): {e}")
                return None
        return self._engine
    
    def reset_engine(self):
        """Force engine reload (call after repeated failures)."""
        self._engine = None

    def fetch(self) -> dict:
        """Fetch ALL MerCu endpoints. Returns complete data dict."""
        now = time.time()
        if now - self._last_fetch_time < self._fetch_interval:
            return self._data_cache

        try:
            engine = self.engine
            if engine is None:
                return {}

            # Fetch all 9 endpoints via engine.client (which has get_* methods) or get_all_data()
            if hasattr(engine, 'get_all_data'):
                data = engine.get_all_data()
            else:
                cl = engine.client if hasattr(engine, 'client') else engine
                data = {
                    "anomalies": cl.get_anomalies(limit=100) if hasattr(cl, 'get_anomalies') else [],
                    "momentum": cl.get_momentum() if hasattr(cl, 'get_momentum') else {},
                    "surge": cl.get_surge(limit=20) if hasattr(cl, 'get_surge') else [],
                    "rank": cl.get_rank() if hasattr(cl, 'get_rank') else {},
                    "plaza": cl.get_plaza(limit=20) if hasattr(cl, 'get_plaza') else [],
                    "deep": cl.get_deep(limit=10) if hasattr(cl, 'get_deep') else [],
                    "briefs": cl.get_briefs() if hasattr(cl, 'get_briefs') else [],
                    "dashboard": cl.get_dashboard() if hasattr(cl, 'get_dashboard') else {},
                    "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")
                }

            # Compute derived indicators from MerCu data
            data["indicators"] = self._compute_indicators(data)

            self._data_cache = data
            self._last_fetch_time = now
            self._fetch_errors = 0

            # Emit to EventBus with full stats
            bus = EventBus.get()
            bus.emit(Event(EventType.MERCU_DATA, {
                "anomaly_count": len(data.get("anomalies", [])),
                "surge_count": len(data.get("surge", [])),
                "plaza_count": len(data.get("plaza", [])),
                "deep_count": len(data.get("deep", [])),
                "momentum_boards": len(data.get("momentum", {}).get("boards", {})),
                "rank_entries": len(data.get("rank", {}).get("data", [])),
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

            return self._data_cache

    def _compute_indicators(self, data: dict) -> dict:
        """Compute derived indicators from MerCu data (no exchange needed)."""
        indicators = {}
        
        anomalies = data.get("anomalies", [])
        momentum = data.get("momentum", {})
        boards = momentum.get("boards", {})
        surge = data.get("surge", [])
        plaza = data.get("plaza", [])

        # 1. Momentum strength per coin
        momentum_map = {}
        for side in ("priceUp", "priceDown"):
            for item in boards.get(side, []):
                sym = item.get("sym", "")
                strength = float(item.get("strength", 0))
                resonance = item.get("resonance", [])
                val_str = item.get("val", "0%")
                try:
                    val_pct = float(val_str.replace("%", "").replace("+", ""))
                except ValueError:
                    val_pct = 0.0
                momentum_map[sym] = {
                    "side": "up" if side == "priceUp" else "down",
                    "strength": strength,
                    "change_pct": val_pct,
                    "resonance": resonance,
                    "resonance_count": len(resonance)
                }
        indicators["momentum_map"] = momentum_map

        # 2. Surge rhythm map + derived fields
        surge_map = {}
        for item in surge:
            sym = item.get("sym", "")
            # Parse raw surge data
            rhythm = item.get("rhythm", "")
            accel = float(item.get("accel", 0))
            total = int(item.get("total", 0))
            direction = item.get("dir", "up")
            
            # Derived: bid_wall from surge context (if accel > 1.0 and total > 5 = buying pressure)
            bid_wall = min(25, int(accel * total * 2)) if accel > 1.0 and direction == "up" else 0
            
            # Derived: trap detection from rhythm patterns
            mid_trap = "陷阱" in rhythm and "高" not in rhythm
            high_trap_count = 1 if "高陷阱" in str(item.get("tags", "")) or "高陷阱" in rhythm else 0
            
            # Derived: stage sequence from rhythm patterns
            stage_seq = []
            if "吸筹" in str(item): stage_seq.append("吸筹")
            if "多头" in str(item) or "主升" in str(item): stage_seq.append("多头")
            if "派发" in str(item): stage_seq.append("派发")
            if rhythm: stage_seq.append(rhythm)
            
            surge_map[sym] = {
                "rhythm": rhythm,
                "accel": accel,
                "total": total,
                "dir": direction,
                "bid_wall": bid_wall,
                "mid_trap": mid_trap,
                "high_trap_count": high_trap_count,
                "stage_sequence": stage_seq
            }
        indicators["surge_map"] = surge_map

        # 3. Plaza divergence detection + spot flow
        plaza_map = {}
        for item in plaza:
            sym = item.get("sym", item.get("symbol", ""))
            sentiment = item.get("sentiment", "")
            smart = item.get("smart_money", "")
            
            # Derived: spot_flow from smart money + sentiment
            if "多" in str(smart) and "bull" in str(sentiment).lower():
                spot_flow = "buy"
            elif "空" in str(smart) and "bear" in str(sentiment).lower():
                spot_flow = "sell"
            elif "bull" in str(sentiment).lower():
                spot_flow = "buy"
            elif "bear" in str(sentiment).lower():
                spot_flow = "sell"
            else:
                spot_flow = "neutral"
            
            plaza_map[sym] = {
                "sentiment": sentiment,
                "strength": float(item.get("strength", 0)),
                "smart_money": smart,
                "divergence": item.get("divergence", False),
                "spot_flow": spot_flow
            }
        indicators["plaza_map"] = plaza_map

        # 4. OI flow analysis from anomalies
        oi_flow = {}
        for a in anomalies:
            sym = (a.get("symbol") or a.get("sym", "")).upper()
            if a.get("main_dim") == "oi":
                if sym not in oi_flow:
                    oi_flow[sym] = {"oi_change": 0, "signals": 0, "direction": "neutral"}
                val = a.get("main_value", 0) * a.get("main_direction", 1)
                oi_flow[sym]["oi_change"] += val
                oi_flow[sym]["signals"] += 1
            if a.get("main_dim") == "vol" and a.get("main_direction", 0) > 0:
                if sym not in oi_flow:
                    oi_flow[sym] = {"oi_change": 0, "signals": 0, "direction": "neutral"}
                oi_flow[sym]["vol_signal"] = True
        
        # Compute OI direction
        for sym, data in oi_flow.items():
            data["direction"] = "up" if data["oi_change"] > 0 else "down" if data["oi_change"] < 0 else "neutral"
        
        indicators["oi_flow"] = oi_flow

        # 5. CVD proxy from momentum + anomaly combo
        cvd_proxy = {}
        for sym, mom in momentum_map.items():
            oi = oi_flow.get(sym, {}).get("oi_change", 0)
            # Strong price up + OI up = strong buying (CVD proxy positive)
            # Strong price down + OI down = strong selling (CVD proxy negative)
            if mom["side"] == "up" and oi > 0:
                cvd_proxy[sym] = "strong_buy"
            elif mom["side"] == "down" and oi < 0:
                cvd_proxy[sym] = "strong_sell"
            elif mom["side"] == "up":
                cvd_proxy[sym] = "buy"
            elif mom["side"] == "down":
                cvd_proxy[sym] = "sell"
        indicators["cvd_proxy"] = cvd_proxy

        return indicators

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

    # 1. Get singletons (DO NOT reset - preserves subscriber registrations)
    # EventBus.reset() is only for tests; in production we keep subscribers alive

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






