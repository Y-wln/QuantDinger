"""Hermes API Routes - Health, signals, and risk status endpoints.

Register with Flask blueprint:
  from app.routes.hermes_api import hermes_bp
  app.register_blueprint(hermes_bp, url_prefix="/api/hermes")
"""
from __future__ import annotations
from flask import Blueprint, jsonify, request
from datetime import datetime, timezone, timedelta
import logging

BJT = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)

hermes_bp = Blueprint("hermes", __name__)


def _get_runner():
    """Get HermesRunner singleton if running."""
    try:
        from app.services.hermes_strategies.runner import HermesRunner
        # HermesRunner is not a singleton, but we can check if one is active
        from app.services.hermes_strategies.event_bus import EventBus
        bus = EventBus.get()
        return bus
    except Exception:
        return None


def _get_risk_engine():
    """Get RiskEngine singleton."""
    try:
        from app.services.hermes_strategies.risk_engine import RiskEngine
        return RiskEngine.get()
    except Exception:
        return None


# ── Health check ──────────────────────────────────────────────

@hermes_bp.route("/health", methods=["GET"])
def health_check():
    """Get full system health status."""
    try:
        from app.services.hermes_strategies.event_bus import EventBus, EventType
        from app.services.hermes_strategies.risk_engine import RiskEngine

        bus = EventBus.get()
        risk = RiskEngine.get()

        # Collect health info
        history = bus.get_history(limit=10)
        error_counts = bus.get_error_counts()
        risk_status = risk.get_status()

        # Check if system appears alive (has recent events)
        recent_events = [e for e in history 
                        if (datetime.now(BJT) - datetime.strptime(e.timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BJT)).total_seconds() < 300]

        return jsonify({
            "status": "ok" if len(recent_events) > 0 or not error_counts else "stale",
            "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
            "event_bus": {
                "subscribers": bus.subscriber_count(),
                "recent_events": len(recent_events),
                "error_counts": error_counts
            },
            "risk_engine": risk_status,
            "components": {
                "event_bus": "alive",
                "risk_engine": "alive",
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")
        }), 500


# ── Risk status ───────────────────────────────────────────────

@hermes_bp.route("/risk", methods=["GET"])
def risk_status():
    """Get risk engine status."""
    try:
        from app.services.hermes_strategies.risk_engine import RiskEngine
        risk = RiskEngine.get()
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S"),
            **risk.get_status()
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── Risk config update ───────────────────────────────────────

@hermes_bp.route("/risk/config", methods=["POST"])
def update_risk_config():
    """Update risk parameters at runtime."""
    try:
        from app.services.hermes_strategies.risk_engine import RiskEngine, RiskConfig
        data = request.get_json() or {}

        risk = RiskEngine.get()
        cfg = risk.config

        # Update only provided fields
        for field in ["max_positions", "min_score_long", "min_score_short",
                       "max_daily_loss_pct", "max_drawdown_pct",
                       "cooldown_minutes", "max_consecutive_losses",
                       "max_position_pct", "max_total_exposure_pct"]:
            if field in data:
                setattr(cfg, field, data[field])

        return jsonify({
            "status": "ok",
            "message": "Risk config updated",
            "config": {
                "max_positions": cfg.max_positions,
                "min_score_long": cfg.min_score_long,
                "min_score_short": cfg.min_score_short,
                "max_daily_loss_pct": cfg.max_daily_loss_pct,
                "max_drawdown_pct": cfg.max_drawdown_pct,
                "cooldown_minutes": cfg.cooldown_minutes
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── Recent signals ───────────────────────────────────────────

@hermes_bp.route("/signals", methods=["GET"])
def recent_signals():
    """Get recent signals from EventBus history."""
    try:
        from app.services.hermes_strategies.event_bus import EventBus, EventType

        bus = EventBus.get()
        limit = request.args.get("limit", 50, type=int)
        signal_type = request.args.get("type", None)

        event_type = None
        if signal_type:
            try:
                event_type = EventType(signal_type)
            except ValueError:
                pass

        events = bus.get_history(event_type=event_type, limit=limit)

        return jsonify({
            "status": "ok",
            "count": len(events),
            "signals": [
                {
                    "type": e.type.value,
                    "source": e.source,
                    "timestamp": e.timestamp,
                    "data": e.data
                }
                for e in events
            ]
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── Circuit breaker control ──────────────────────────────────

@hermes_bp.route("/breaker/reset", methods=["POST"])
def reset_breaker():
    """Manually reset the circuit breaker."""
    try:
        from app.services.hermes_strategies.risk_engine import RiskEngine
        risk = RiskEngine.get()
        if risk.breaker.is_open:
            risk.breaker.tripped_at = None
            risk.breaker.trip_reason = ""
            return jsonify({"status": "ok", "message": "Circuit breaker reset"})
        return jsonify({"status": "ok", "message": "Circuit breaker was not tripped"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
