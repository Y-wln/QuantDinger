"""Hermes Strategies Registry - Event-driven modular architecture.

New v3 architecture:
  event_bus.py  → Decoupled pub/sub communication
  risk_engine.py → Position sizing, drawdown, circuit breaker  
  runner.py     → Unified daemon replacing orchestrator+watchdog
  base.py       → Strategy interface + signal dataclass
  *_v2.py       → Strategy implementations (demon, ambush, lightning, dag)

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

# Subscribers (auto-register via @on decorators when imported)
from . import subscribers  # noqa: F401

# ── Strategy Registry ──────────────────────────────────────

STRATEGIES = [
    DemonV2(),      # 妖币猎手
    AmbushV2(),     # 埋伏策略
]

DAG = DAGConsensusV2()  # DAG共识过滤器

def get_all_strategies():
    return STRATEGIES

def get_dag():
    return DAG

# ── Quick-start helper ─────────────────────────────────────

def create_runner(mercu_fetcher=None, risk_config: Optional[RiskConfig] = None) -> HermesRunner:
    """Create a fully configured runner with all modules wired."""
    # NOTE: Do NOT EventBus.reset() here - it kills subscribers
    RiskEngine.reset()

    bus = EventBus.get()
    risk = RiskEngine.get(risk_config or RiskConfig())
    runner = HermesRunner()
    runner.load_from_registry()

    health = HealthReporter(runner, interval_seconds=60)
    health.start()

    def _fetch():
        if mercu_fetcher:
            return mercu_fetcher()
        return {}

    return runner, _fetch

# ── Exports ────────────────────────────────────────────────

__all__ = [
    "BaseStrategy", "StrategySignal", "BJT",
    "EventBus", "Event", "EventType", "on",
    "RiskEngine", "RiskConfig", "RiskVerdict", "CircuitBreaker",
    "HermesRunner", "HealthReporter", "ComponentHealth",
    "DemonV2", "AmbushV2", "DAGConsensusV2",
    "STRATEGIES", "DAG",
    "get_all_strategies", "get_dag", "create_runner",
]



