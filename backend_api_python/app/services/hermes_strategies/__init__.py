"""Hermes Strategies Registry - Event-driven modular architecture.

New v3 architecture:
  event_bus.py     -> Decoupled pub/sub communication
  risk_engine.py   -> Position sizing, drawdown, circuit breaker  
  runner.py        -> Unified daemon replacing orchestrator+watchdog
  signal_tracker.py-> Full lifecycle signal tracking + accuracy analysis
  subscribers.py   -> Feishu alerts, signal logging, health monitor
  base.py          -> Strategy interface + signal dataclass
  *_v2.py          -> Strategy implementations (demon, ambush, lightning, dag)

Usage:
  from app.services.hermes_strategies import (
      HermesRunner, RiskEngine, EventBus, EventType,
      get_all_strategies, get_dag
  )
  
  runner = HermesRunner()
  runner.load_from_registry()
  runner.start(mercu_data_provider=your_data_func)
"""
from typing import Optional
from .base import BaseStrategy, StrategySignal, BJT
from .event_bus import EventBus, Event, EventType, on
from .risk_engine import RiskEngine, RiskConfig, RiskVerdict, CircuitBreaker
from .position_manager import PositionManager, Position
from .signal_tracker import SignalTracker
from .runner import HermesRunner, HealthReporter, ComponentHealth

# Strategy imports
from .dag_v2 import DAGConsensusV2
from .ambush_v3 import AmbushV3
from .demon_v3 import DemonV3
from .early_signals import (run_all_early_signals, get_early_entry_score, classify_stage)
# lightning_v2 disabled - backtest showed 12-33% accuracy

# ── Strategy Registry ──────────────────────────────────────

STRATEGIES = [
    DemonV3(),      # 妖币猎手
    AmbushV3(),     # 埋伏策略
]

DAG = DAGConsensusV2()

def get_all_strategies():
    return STRATEGIES

def get_dag():
    return DAG

# ── Subscribers (explicit init to avoid import-time side effects) ──

_subscribers_loaded = False

def init_subscribers():
    """Initialize EventBus subscribers (signal logging, Feishu alerts, health monitor).
    
    Called explicitly by hermes_daemon.py at startup.
    Not called at import time to avoid file I/O during module loading.
    """
    global _subscribers_loaded
    if _subscribers_loaded:
        return
    import time as _time; _t0 = _time.time()
    from . import subscribers  # noqa: F401 - registers @on handlers
    import logging; _log = logging.getLogger(__name__); _log.info(f"subscribers imported in {_time.time()-_t0:.3f}s")
    _subscribers_loaded = True

# ── Quick-start helper ─────────────────────────────────────

def create_runner(mercu_fetcher=None, risk_config: Optional[RiskConfig] = None):
    """Create a fully configured runner with all modules wired."""
    RiskEngine.reset()
    risk = RiskEngine.get(risk_config or RiskConfig())
    runner = HermesRunner()
    runner.load_from_registry()
    health = HealthReporter(runner, interval_seconds=60)
    health.start()
    return runner, lambda: mercu_fetcher() if mercu_fetcher else {}

# ── Exports ────────────────────────────────────────────────

__all__ = [
    "BaseStrategy", "StrategySignal", "BJT",
    "EventBus", "Event", "EventType", "on",
    "RiskEngine", "RiskConfig", "RiskVerdict", "CircuitBreaker",
    "HermesRunner", "HealthReporter", "ComponentHealth",
    "DemonV3", "AmbushV3", "DAGConsensusV2",
    "STRATEGIES", "DAG",
    "get_all_strategies", "get_dag", "create_runner", "init_subscribers",
    "init_subscribers",
]




# ── V3 Startup (replaces hermes_strategy_service.py) ──────────

_hermes_v3_runner: Optional[object] = None
_hermes_v3_started: bool = False

def start_hermes_v3():
    """Start Hermes V3 trading system.
    
    Wires together:
      MerCuDataBridge → EventBus → Strategies → RiskEngine → QD Bridge
    Called once at QD app startup.
    """
    global _hermes_v3_runner, _hermes_v3_started
    if _hermes_v3_started:
        return
    
    import os, logging, threading
    _log = logging.getLogger(__name__)
    
    # Avoid double-start with Flask reloader
    debug = os.getenv("PYTHON_API_DEBUG", "false").lower() == "true"
    if debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    
    try:
        # 1. Init subscribers (Feishu, logging, health)
        init_subscribers()
        
        # 2. Import PositionManager + create runner with strategies
        from .position_manager import PositionManager
        EventBus.reset()
        RiskEngine.reset()
        PositionManager.reset()
        
        runner = HermesRunner()
        runner.load_from_registry()
        
        # 3. Start MerCu data bridge in background thread
        from .hermes_daemon import MerCuDataBridge
        bridge = MerCuDataBridge()
        
        def mercu_poll_loop():
            while runner._running if hasattr(runner, "_running") else True:
                try:
                    data = bridge.fetch()
                    bus = EventBus.get()
                    bus.emit(Event(type=EventType.MERCU_DATA, data=data, source="mercu_bridge"))
                    
                    # Merge engine signals (21+ doc-based scores) into data
                    if bridge.engine:
                        engine_signals = bridge.engine.generate_signals()
                        if engine_signals:
                            data["engine_signals"] = engine_signals
                            for es in engine_signals:
                                bus.emit(Event(type=EventType.SIGNAL_GENERATED, 
                                    data=es, source="engine"))
                    
                    runner._run_cycle(mercu_data_provider=lambda: data)
                except Exception as e:
                    _log.error(f"MerCu poll error: {e}")
                import time; time.sleep(30)
        
        runner._running = True
        poll_thread = threading.Thread(target=mercu_poll_loop, daemon=True, name="mercu-poll")
        poll_thread.start()
        
        # 4. Start health reporter
        health = HealthReporter(runner, interval_seconds=60)
        health.start()
        
        # 5. Wire QD bridge (auto-execution, notifications, portfolio)
        from .hermes_qd_bridge import integrate_with_quantdinger
        bridge_result = integrate_with_quantdinger()
        
        _hermes_v3_runner = runner
        _hermes_v3_started = True
        
        _log.info(f"Hermes V3 started: strategies={len(get_all_strategies())}, "
                  f"bridge={bridge_result.get('execution','unknown')}")
    except Exception as e:
        _log.error(f"Hermes V3 startup failed: {e}", exc_info=True)


def get_hermes_v3_status() -> dict:
    """Get V3 system status."""
    global _hermes_v3_runner, _hermes_v3_started
    if not _hermes_v3_started:
        return {"status": "not_started"}
    try:
        from .position_manager import PositionManager
        pm = PositionManager.get()
        risk = RiskEngine.get()
        bus = EventBus.get()
        return {
            "status": "running",
            "positions": pm.get_status(),
            "risk": risk.get_status(),
            "event_bus_subscribers": bus.subscriber_count(),
            "event_bus_errors": bus.get_error_counts(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}






