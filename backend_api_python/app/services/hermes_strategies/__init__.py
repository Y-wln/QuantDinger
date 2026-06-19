"""Hermes Strategies Registry - Loads all strategy modules."""
from .base import BaseStrategy, StrategySignal, BJT
from .lightning_v2 import LightningV2
from .dag_v2 import DAGConsensusV2
from .ambush_v2 import AmbushV2
from .demon_v2 import DemonV2

# Strategy registry - ordered by priority
STRATEGIES = [
    LightningV2(),
    DemonV2(),
    AmbushV2(),
]

# DAG filter (applied after signal generation)
DAG = DAGConsensusV2()

def get_all_strategies():
    return STRATEGIES

def get_dag():
    return DAG
