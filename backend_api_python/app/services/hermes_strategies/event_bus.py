"""Event Bus - lightweight pub/sub for decoupled strategy communication.

All components emit/listen to typed events instead of calling each other directly.
This prevents cascading failures when one module crashes.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading
import traceback

BJT = timezone(timedelta(hours=8))


class EventType(Enum):
    """All event types in the trading system."""
    # Data events
    MARKET_DATA = "market_data"           # New kline/price data
    MERCU_DATA = "mercu_data"             # MerCu signal data refreshed
    NEWS_DATA = "news_data"               # Jin10 news update

    # Strategy events
    SIGNAL_GENERATED = "signal_generated" # Strategy produced a signal
    SIGNAL_FILTERED = "signal_filtered"   # DAG consensus filtered signal
    SIGNAL_DROPPED = "signal_dropped"     # Signal rejected

    # Execution events
    ORDER_REQUESTED = "order_requested"   # Strategy wants to place order
    ORDER_FILLED = "order_filled"         # Exchange confirmed fill
    ORDER_REJECTED = "order_rejected"     # Exchange rejected order

    # Risk events  
    RISK_BLOCKED = "risk_blocked"         # RiskEngine blocked a trade
    CIRCUIT_BREAKER = "circuit_breaker"   # Circuit breaker tripped

    # System events
    HEARTBEAT = "heartbeat"               # Component alive check
    ERROR = "error"                       # Component error
    SHUTDOWN = "shutdown"                 # Graceful shutdown


@dataclass
class Event:
    """Immutable event envelope."""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")


class EventBus:
    """Thread-safe pub/sub event bus.

    Usage:
        bus = EventBus.get()
        bus.subscribe(EventType.SIGNAL_GENERATED, my_handler)
        bus.emit(Event(EventType.SIGNAL_GENERATED, {"symbol": "BTC"}))
    """

    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._history: List[Event] = []  # Last N events for replay
        self._max_history = 500
        self._error_count: Dict[str, int] = defaultdict(int)
        self._emit_lock = threading.Lock()

    @classmethod
    def get(cls) -> "EventBus":
        """Singleton access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = EventBus()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        with cls._lock:
            cls._instance = None

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Subscribe handler to an event type. Handler receives Event object."""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """Remove handler subscription."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def emit(self, event: Event):
        """Emit event to all subscribers. Errors in handlers are caught."""
        with self._emit_lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self._error_count[event.source] += 1
                # Don't let one bad handler crash others
                traceback.print_exc()

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 50) -> List[Event]:
        """Get recent events, optionally filtered by type."""
        if event_type:
            return [e for e in self._history if e.type == event_type][-limit:]
        return self._history[-limit:]

    def get_error_counts(self) -> Dict[str, int]:
        """Get per-component error counts."""
        return dict(self._error_count)

    def clear_errors(self):
        """Reset error counters."""
        self._error_count.clear()

    def subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        """Count subscribers, optionally for a specific event type."""
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(h) for h in self._subscribers.values())


# Convenience: decorator to auto-subscribe
def on(event_type: EventType):
    """Decorator: auto-subscribe a function to an EventType.

    Usage:
        @on(EventType.SIGNAL_GENERATED)
        def handle_signal(event: Event):
            print(f"Got signal: {event.data}")
    """
    def decorator(func: Callable[[Event], None]):
        EventBus.get().subscribe(event_type, func)
        return func
    return decorator
