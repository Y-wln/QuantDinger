"""Hermes Runner - unified daemon that runs all strategies with event-driven architecture.

Replaces scattered daemon.py + orchestrator.py + watchdog.py.
Uses EventBus for all inter-module communication.
All signals pass through RiskEngine before execution.
"""
from __future__ import annotations
import time as time_module
import threading
import traceback
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from .event_bus import EventBus, Event, EventType, on
from .risk_engine import RiskEngine, RiskConfig, RiskVerdict
from .base import BaseStrategy, StrategySignal

BJT = timezone(timedelta(hours=8))


class ComponentHealth:
    """Tracks health of a single component."""
    def __init__(self, name: str, max_stale_seconds: int = 120):
        self.name = name
        self.max_stale = max_stale_seconds
        self.last_heartbeat: float = time_module.time()
        self.error_count: int = 0
        self.status: str = "alive"  # alive / stale / dead
        self.last_error: str = ""

    def heartbeat(self):
        self.last_heartbeat = time_module.time()
        self.status = "alive"

    def record_error(self, msg: str):
        self.error_count += 1
        self.last_error = msg

    @property
    def is_alive(self) -> bool:
        return (time_module.time() - self.last_heartbeat) < self.max_stale

    @property
    def age_seconds(self) -> float:
        return time_module.time() - self.last_heartbeat


class HermesRunner:
    """Unified strategy runner. One instance per process.

    Responsibilities:
    - Load strategies from registry
    - Poll MerCu data on interval
    - Run strategies → generate signals
    - Filter through DAG consensus
    - Risk check every signal
    - Emit events for tracking/alerting
    - Health monitoring on all components
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.bus = EventBus.get()
        self.risk = RiskEngine.get(RiskConfig())

        # Component tracking
        self._components: Dict[str, ComponentHealth] = {}
        self._register_component("runner", max_stale=300)
        self._register_component("mercu_data", max_stale=120)
        self._register_component("strategies", max_stale=120)
        self._register_component("risk_engine", max_stale=120)

        # Strategy management
        self._strategies: List[BaseStrategy] = []
        self._dag = None

        # State
        self._running = False
        self._cycle_count: int = 0
        self._cycle_interval: int = self.config.get("cycle_interval_seconds", 30)
        self._signal_log: List[Dict] = []
        self._max_log_entries: int = 2000
        self._lock = threading.Lock()

        # Stats
        self._signals_generated: int = 0
        self._signals_approved: int = 0
        self._signals_blocked: int = 0
        self._start_time: Optional[float] = None

    # ── Component management ──────────────────────────────────

    def _register_component(self, name: str, max_stale: int = 120):
        self._components[name] = ComponentHealth(name, max_stale)

    def heartbeat(self, component: str):
        """Call from any component to signal it's alive."""
        if component in self._components:
            self._components[component].heartbeat()
        self.bus.emit(Event(EventType.HEARTBEAT, {"component": component}, source=component))

    # ── Strategy loading ──────────────────────────────────────

    def load_strategies(self, strategies: List[BaseStrategy], dag=None):
        """Load strategies to run."""
        self._strategies = strategies
        self._dag = dag

    def load_from_registry(self):
        """Auto-load from strategy registry."""
        try:
            from . import get_all_strategies, get_dag
            self._strategies = get_all_strategies()
            self._dag = get_dag()
        except Exception as e:
            self._components["strategies"].record_error(str(e))

    # ── Main loop ─────────────────────────────────────────────

    def start(self, mercu_data_provider=None):
        """Start the main loop. Runs in current thread."""
        self._running = True
        self._start_time = time_module.time()
        self.heartbeat("runner")

        while self._running:
            cycle_start = time_module.time()
            try:
                self._run_cycle(mercu_data_provider)
                self._cycle_count += 1
                self.heartbeat("runner")
                self.heartbeat("strategies")
            except Exception as e:
                self._components["runner"].record_error(str(e))
                self.bus.emit(Event(EventType.ERROR, {
                    "component": "runner",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }, source="runner"))
                traceback.print_exc()

            # Sleep until next cycle
            elapsed = time_module.time() - cycle_start
            sleep_time = max(0.5, self._cycle_interval - elapsed)
            time_module.sleep(sleep_time)

    def stop(self):
        """Graceful shutdown."""
        self._running = False
        self.bus.emit(Event(EventType.SHUTDOWN, {
            "cycles": self._cycle_count,
            "uptime_seconds": int(time_module.time() - (self._start_time or time_module.time()))
        }, source="runner"))

    def _run_cycle(self, mercu_data_provider=None):
        """One cycle: fetch data → generate → filter → risk check."""
        # 1. Fetch MerCu data
        mercu_data = {}
        try:
            if mercu_data_provider:
                mercu_data = mercu_data_provider()
            self.heartbeat("mercu_data")
        except Exception as e:
            self._components["mercu_data"].record_error(str(e))
            self.bus.emit(Event(EventType.ERROR, {
                "component": "mercu_data",
                "error": str(e)
            }, source="mercu_data"))

        if not mercu_data:
            return

        # 2. Run each strategy
        for strategy in self._strategies:
            try:
                signals = strategy.generate(mercu_data)
                for sig in signals:
                    self._process_signal(sig, strategy.name)
            except Exception as e:
                self._components["strategies"].record_error(str(e))
                self.bus.emit(Event(EventType.ERROR, {
                    "component": f"strategy.{strategy.name}",
                    "error": str(e)
                }, source=strategy.name))

        # 3. DAG consensus (if loaded)
        if self._dag and len(self._signal_log) > 0:
            try:
                # Get latest signals this cycle
                recent = [s for s in self._signal_log[-20:] 
                         if s.get("stage") != "risk_blocked"]
                self._dag.analyze(mercu_data, recent)
            except Exception as e:
                pass

        self.heartbeat("risk_engine")

    def _process_signal(self, sig: StrategySignal, source: str):
        """Process a single signal through risk check."""
        self._signals_generated += 1

        # Emit raw signal
        event_data = sig.to_dict()
        event_data["source"] = source
        self.bus.emit(Event(EventType.SIGNAL_GENERATED, event_data, source=source))

        # Risk check
        verdict = self.risk.check_signal(
            symbol=sig.symbol,
            direction=sig.direction,
            score=sig.score,
            price=sig.price
        )

        # Log
        log_entry = {
            **sig.to_dict(),
            "source": source,
            "risk_approved": verdict.approved,
            "risk_reason": verdict.reason,
            "risk_warnings": verdict.warnings,
            "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
            "cycle": self._cycle_count
        }

        with self._lock:
            self._signal_log.append(log_entry)
            if len(self._signal_log) > self._max_log_entries:
                self._signal_log = self._signal_log[-self._max_log_entries:]

        if verdict.approved:
            self._signals_approved += 1
            self.risk.record_trade_attempt()
            self.bus.emit(Event(EventType.SIGNAL_FILTERED, {
                **sig.to_dict(),
                "risk_warnings": verdict.warnings,
                "adjusted_size": verdict.adjusted_size_pct
            }, source="risk_engine"))
        else:
            self._signals_blocked += 1
            self.bus.emit(Event(EventType.RISK_BLOCKED, {
                **sig.to_dict(),
                "reason": verdict.reason,
                "warnings": verdict.warnings
            }, source="risk_engine"))

    # ── Health & Status ───────────────────────────────────────

    def get_health(self) -> dict:
        """Full health report for all components."""
        components = {}
        dead_count = 0
        for name, comp in self._components.items():
            alive = comp.is_alive
            if not alive:
                dead_count += 1
            components[name] = {
                "status": comp.status if alive else "⚠️ STALE",
                "alive": alive,
                "age_seconds": round(comp.age_seconds, 0),
                "error_count": comp.error_count,
                "last_error": comp.last_error[-100:] if comp.last_error else ""
            }

        uptime = int(time_module.time() - (self._start_time or time_module.time()))

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "cycles": self._cycle_count,
            "components": components,
            "dead_components": dead_count,
            "signals": {
                "generated": self._signals_generated,
                "approved": self._signals_approved,
                "blocked": self._signals_blocked,
                "approval_rate": round(
                    self._signals_approved / max(1, self._signals_generated) * 100, 1
                )
            },
            "risk": self.risk.get_status(),
            "bus_subscribers": self.bus.subscriber_count()
        }

    def get_recent_signals(self, limit: int = 20) -> List[Dict]:
        """Get recent signal log entries."""
        with self._lock:
            return self._signal_log[-limit:]

    def get_stats(self) -> dict:
        """Running statistics."""
        return {
            "cycles": self._cycle_count,
            "signals_generated": self._signals_generated,
            "signals_approved": self._signals_approved,
            "signals_blocked": self._signals_blocked,
            "strategies_loaded": len(self._strategies),
            "strategy_names": [s.name for s in self._strategies]
        }


# ── Health reporter (runs in background thread) ─────────────

class HealthReporter:
    """Background thread that periodically emits health status."""

    def __init__(self, runner: HermesRunner, interval_seconds: int = 60):
        self.runner = runner
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
            time_module.sleep(self.interval)
            try:
                health = self.runner.get_health()
                bus = EventBus.get()
                bus.emit(Event(EventType.HEARTBEAT, health, source="health_reporter"))

                # Auto-trip circuit breaker if too many dead components
                if health["dead_components"] >= 3:
                    bus.emit(Event(EventType.ERROR, {
                        "component": "health_reporter",
                        "error": f"{health['dead_components']} dead components detected",
                        "details": health["components"]
                    }, source="health_reporter"))
            except Exception:
                pass
