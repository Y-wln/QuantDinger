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
from .runner import HermesRunner, HealthReporter, ComponentHealth

# Strategy imports
from .dag_v2 import DAGConsensusV2
from .ambush_v2 import AmbushV2
from .demon_v2 import DemonV2
# lightning_v2 disabled - backtest showed 12-33% accuracy

# ── Strategy Registry ──────────────────────────────────────

STRATEGIES = [
    DemonV2(),      # 妖币猎手
    AmbushV2(),     # 埋伏策略
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
    "DemonV2", "AmbushV2", "DAGConsensusV2",
    "STRATEGIES", "DAG",
    "get_all_strategies", "get_dag", "create_runner", "init_subscribers",
    "init_subscribers",
]


