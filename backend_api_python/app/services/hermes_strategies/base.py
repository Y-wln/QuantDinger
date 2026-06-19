"""Hermes Strategy Module - Unified strategy interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

@dataclass
class StrategySignal:
    symbol: str
    direction: str  # LONG / SHORT / NEUTRAL
    score: int
    price: float = 0.0
    stage: str = ""
    reasons: List[str] = field(default_factory=list)
    source: str = ""
    timestamp: str = ""
    confidence: str = "medium"  # low/medium/high

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "direction": self.direction,
            "score": self.score, "price": self.price,
            "stage": self.stage, "reasons": self.reasons,
            "source": self.source, "timestamp": self.timestamp,
            "confidence": self.confidence
        }

class BaseStrategy(ABC):
    def __init__(self, name: str): self.name = name

    @abstractmethod
    def generate(self, mercu_data: dict) -> List[StrategySignal]:
        """Generate signals from MerCu data."""
        ...

    def get_status(self) -> dict:
        return {"name": self.name, "active": True}
