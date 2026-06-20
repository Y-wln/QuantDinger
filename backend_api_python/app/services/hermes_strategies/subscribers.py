"""EventBus Subscribers - signal logging, Feishu alerts, and tracking.

These subscribers auto-register when imported. They listen to EventBus events
and route them to the appropriate output channels.

To enable: just import this module in hermes_daemon.py or __init__.py
"""
from __future__ import annotations
import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .event_bus import EventBus, Event, EventType, on

BJT = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)

# ── Signal Logger (writes to JSONL file) ──────────────────────

class SignalLogger:
    """Persists all signals to a JSONL file for backtesting and analysis."""

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "signals.jsonl"))
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self._count = 0

    def log(self, event: Event):
        try:
            entry = {
                "type": event.type.value,
                "source": event.source,
                "timestamp": event.timestamp,
                **event.data
            }
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._count += 1
        except Exception as e:
            logger.error(f"SignalLogger error: {e}")

    @property
    def count(self) -> int:
        return self._count


_signal_logger = SignalLogger()


@on(EventType.SIGNAL_GENERATED)
def _log_signal(event: Event):
    _signal_logger.log(event)


@on(EventType.SIGNAL_FILTERED)
def _log_filtered(event: Event):
    _signal_logger.log(event)


@on(EventType.RISK_BLOCKED)
def _log_blocked(event: Event):
    _signal_logger.log(event)


# ── Feishu Alert Bridge ──────────────────────────────────────

class FeishuBridge:
    """Sends critical events to Feishu webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self._cooldown: dict = {}  # event_type -> last_send_time
        self._cooldown_seconds: int = 60  # Don't spam same event type

    def set_webhook(self, url: str):
        self.webhook_url = url

    def send(self, title: str, content: str, event_type: str = "default"):
        """Send a Feishu message. Rate-limited by event_type."""
        import time
        import urllib.request

        if not self.webhook_url:
            return

        now = time.time()
        last = self._cooldown.get(event_type, 0)
        if now - last < self._cooldown_seconds:
            return  # Rate limited

        self._cooldown[event_type] = now

        try:
            payload = json.dumps({
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": title},
                        "template": "red" if "ERROR" in title.upper() or "CIRCUIT" in title.upper() else "blue"
                    },
                    "elements": [
                        {"tag": "div", "text": {"tag": "lark_md", "content": content}}
                    ]
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                self.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.error(f"Feishu send error: {e}")


_feishu = FeishuBridge()


def set_feishu_webhook(url: str):
    """Configure Feishu webhook URL for alerts."""
    _feishu.set_webhook(url)


@on(EventType.CIRCUIT_BREAKER)
def _on_circuit_breaker(event: Event):
    reason = event.data.get("reason", "Unknown")
    _feishu.send(
        "🛑 断路器熔断",
        f"原因: {reason}\n时间: {event.timestamp}\n系统已暂停交易",
        "circuit_breaker"
    )


@on(EventType.ERROR)
def _on_error(event: Event):
    component = event.data.get("component", "unknown")
    error = event.data.get("error", "")
    # Only alert on critical errors
    if "DEAD" in str(error).upper() or "STALE" in str(error).upper():
        _feishu.send(
            "⚠️ 组件异常",
            f"组件: {component}\n错误: {error}\n时间: {event.timestamp}",
            "critical_error"
        )


# ── Health Monitor (tracks component liveness) ────────────────

class HealthMonitor:
    """Watches heartbeats and alerts on stale/dead components."""

    def __init__(self):
        self._last_alerts: dict = {}  # component -> last alert time
        self._alert_interval: int = 300  # 5 min between repeat alerts

    def check(self, event: Event):
        import time
        data = event.data
        if isinstance(data, dict) and "components" in data:
            # This is a full health report
            dead = []
            for name, comp in data.get("components", {}).items():
                if not comp.get("alive", True):
                    dead.append(f"  ❌ {name}: {comp.get('status', 'DEAD')} (age={comp.get('age_seconds', 0)}s)")

            if dead:
                now = time.time()
                key = "health_report"
                if now - self._last_alerts.get(key, 0) > self._alert_interval:
                    self._last_alerts[key] = now
                    _feishu.send(
                        "🚨 组件死亡告警",
                        "\n".join(dead),
                        "health_alert"
                    )


_health_monitor = HealthMonitor()


@on(EventType.HEARTBEAT)
def _on_health_report(event: Event):
    _health_monitor.check(event)


# ── Exports ──────────────────────────────────────────────────
__all__ = [
    "SignalLogger", "_signal_logger",
    "FeishuBridge", "_feishu", "set_feishu_webhook",
    "HealthMonitor",
]



