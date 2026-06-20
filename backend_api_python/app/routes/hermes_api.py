"""Hermes V3 API Routes - complete REST API (17 endpoints).

Replaces both hermes.py (V2) and hermes_api.py (V3 partial).
Register with Flask blueprint:
  from app.routes.hermes_api import hermes_bp
  app.register_blueprint(hermes_bp, url_prefix="/api/hermes")
"""
from __future__ import annotations
from flask import Blueprint, jsonify, request
from datetime import datetime, timezone, timedelta
import logging
import os

BJT = timezone(timedelta(hours=8))
logger = logging.getLogger(__name__)
hermes_bp = Blueprint("hermes", __name__)


# ── Helpers ───────────────────────────────────────────────────

def _get_bus():
    try:
        from app.services.hermes_strategies.event_bus import EventBus
        return EventBus.get()
    except Exception:
        return None

def _get_risk():
    try:
        from app.services.hermes_strategies.risk_engine import RiskEngine
        return RiskEngine.get()
    except Exception:
        return None

def _get_pm():
    try:
        from app.services.hermes_strategies.position_manager import PositionManager
        return PositionManager.get()
    except Exception:
        return None

def _get_tracker():
    try:
        from app.services.hermes_strategies.signal_tracker import SignalTracker
        return SignalTracker.get()
    except Exception:
        return None

def _get_engine():
    try:
        from app.data_providers.hermes_mercu import get_hermes_engine
        return get_hermes_engine()
    except Exception:
        return None

def _now():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")


# ── 1. Health ─────────────────────────────────────────────────

@hermes_bp.route("/health", methods=["GET"])
def health_check():
    try:
        bus = _get_bus()
        risk = _get_risk()
        pm = _get_pm()
        history = bus.get_history(limit=10) if bus else []
        recent = [e for e in history if _event_age_s(e) < 300]
        return jsonify({
            "status": "ok" if recent or risk else "stale",
            "timestamp": _now(),
            "event_bus": {
                "subscribers": bus.subscriber_count() if bus else 0,
                "recent_events": len(recent),
                "error_counts": bus.get_error_counts() if bus else {},
            },
            "risk_engine": risk.get_status() if risk else {},
            "positions": pm.get_status() if pm else {},
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "timestamp": _now()}), 500

def _event_age_s(e):
    try:
        ts = datetime.strptime(e.timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BJT)
        return (datetime.now(BJT) - ts).total_seconds()
    except Exception:
        return 999


# ── 2. Signals ────────────────────────────────────────────────

@hermes_bp.route("/signals", methods=["GET"])
def get_signals():
    """Get current Hermes/MerCu trading signals."""
    try:
        engine = _get_engine()
        limit = request.args.get("limit", 20, type=int)
        min_score = request.args.get("min_score", 5, type=int)
        signals = engine.generate_signals() if engine else []
        signals = [s for s in signals if abs(s.get("score", 0)) >= min_score]
        return jsonify({"ok": True, "count": len(signals[:limit]), "signals": signals[:limit]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 3. Raw Data ───────────────────────────────────────────────

@hermes_bp.route("/data", methods=["GET"])
def get_raw_data():
    """Get raw MerCu data (anomalies, momentum, surge)."""
    try:
        engine = _get_engine()
        data = engine.get_all_data() if engine else {}
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 4. Score ─────────────────────────────────────────────────

@hermes_bp.route("/score", methods=["POST"])
def score_coin():
    """Score a coin from posted state events."""
    try:
        engine = _get_engine()
        body = request.get_json(silent=True) or {}
        symbol = body.get("symbol", "")
        events = body.get("events", [])
        result = engine.score_events(symbol, events) if engine else {}
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 5. Push ──────────────────────────────────────────────────

@hermes_bp.route("/push", methods=["POST"])
def push_signal():
    """Receive signals from Hermes daemon (push integration)."""
    body = request.get_json(silent=True) or {}
    try:
        from app.services.hermes_strategies.event_bus import EventBus, Event, EventType
        bus = EventBus.get()
        bus.emit(Event(type=EventType.SIGNAL_GENERATED, data=body, source="push_api"))
        return jsonify({"ok": True, "received": body})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 6. Status ─────────────────────────────────────────────────

@hermes_bp.route("/status", methods=["GET"])
def get_status():
    """Get comprehensive system status."""
    try:
        pm = _get_pm()
        risk = _get_risk()
        bus = _get_bus()
        bridge_status = {}
        try:
            from app.services.hermes_strategies.hermes_qd_bridge import get_bridge_status
            bridge_status = get_bridge_status()
        except Exception:
            pass
        return jsonify({
            "ok": True,
            "timestamp": _now(),
            "positions": pm.get_status() if pm else {},
            "risk": risk.get_status() if risk else {},
            "event_bus_errors": bus.get_error_counts() if bus else {},
            "bridge": bridge_status,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 7. Dashboard ──────────────────────────────────────────────

@hermes_bp.route("/dashboard", methods=["GET"])
def get_dashboard():
    """Get dashboard metrics."""
    try:
        from app.services.hermes_strategies.hermes_qd_bridge import get_dashboard_metrics
        return jsonify({"ok": True, "timestamp": _now(), **get_dashboard_metrics()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 8. Risk ──────────────────────────────────────────────────

@hermes_bp.route("/risk", methods=["GET"])
def risk_status():
    try:
        risk = _get_risk()
        return jsonify({"status": "ok", "timestamp": _now(), **risk.get_status()}) if risk else jsonify({"status": "no_engine"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── 9. Risk Config ───────────────────────────────────────────

@hermes_bp.route("/risk/config", methods=["POST"])
def update_risk_config():
    try:
        from app.services.hermes_strategies.risk_engine import RiskEngine, RiskConfig
        data = request.get_json() or {}
        risk = RiskEngine.get()
        for field in ["max_positions", "min_score_long", "min_score_short",
                       "max_daily_loss_pct", "max_drawdown_pct",
                       "cooldown_minutes", "max_consecutive_losses",
                       "max_position_pct", "max_total_exposure_pct"]:
            if field in data:
                setattr(risk.config, field, data[field])
        return jsonify({"status": "ok", "message": "Risk config updated"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── 10. Circuit Breaker ──────────────────────────────────────

@hermes_bp.route("/breaker/reset", methods=["POST"])
def reset_breaker():
    try:
        risk = _get_risk()
        if risk and risk.breaker.is_open:
            risk.breaker.tripped_at = None
            risk.breaker.trip_reason = ""
            return jsonify({"status": "ok", "message": "Circuit breaker reset"})
        return jsonify({"status": "ok", "message": "Not tripped"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── 11-12. Backtest ───────────────────────────────────────────

@hermes_bp.route("/backtest-data", methods=["GET"])
def get_backtest_data():
    """Get backtest-compatible signal data."""
    try:
        tracker = _get_tracker()
        import os
        limit = request.args.get("limit", 200, type=int)
        if tracker:
            history = tracker.get_closed(limit)
            from app.services.hermes_strategies.hermes_qd_bridge import prepare_backtest_data
            bt = prepare_backtest_data(history)
            return jsonify({"ok": True, "count": len(bt), "data": bt})
        # Fallback: read from tracker disk file
        bt_path = os.path.join(os.path.dirname(__file__), "..", "data", "hermes_signal_log.jsonl")
        if os.path.exists(bt_path):
            import json
            lines = []
            with open(bt_path, "r") as f:
                for line in f:
                    if line.strip():
                        lines.append(json.loads(line))
            return jsonify({"ok": True, "count": len(lines[-limit:]), "data": lines[-limit:]})
        return jsonify({"ok": True, "count": 0, "data": []})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_bp.route("/backtest-accuracy", methods=["GET"])
def get_backtest_accuracy():
    """Get signal accuracy from tracker."""
    try:
        tracker = _get_tracker()
        if tracker:
            stats = tracker.get_accuracy_stats()
            return jsonify({"ok": True, **stats})
        return jsonify({"ok": True, "accuracy": 0, "total": 0, "note": "tracker not running"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 13-14. Yaobi Scanner ──────────────────────────────────────

@hermes_bp.route("/yaobi", methods=["GET"])
def get_yaobi():
    """Get yaobi (妖币) signals."""
    try:
        from app.services.hermes_strategies.demon_v3 import DemonV3
        engine = _get_engine()
        data = engine.get_all_data() if engine else {}
        strategy = DemonV3()
        signals = strategy.generate(data)
        return jsonify({
            "ok": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
            "timestamp": _now(),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_bp.route("/yaobi/scan", methods=["POST"])
def trigger_yaobi_scan():
    """Force trigger a yaobi scan."""
    try:
        body = request.get_json(silent=True) or {}
        symbol = body.get("symbol", "")
        from app.services.hermes_strategies.demon_v3 import DemonV3
        engine = _get_engine()
        data = engine.get_all_data() if engine else {}
        strategy = DemonV3()
        signals = strategy.generate(data)
        if symbol:
            signals = [s for s in signals if s.symbol.upper() == symbol.upper()]
        return jsonify({
            "ok": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
            "timestamp": _now(),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 15. Lightning ─────────────────────────────────────────────

@hermes_bp.route("/lightning", methods=["GET"])
def get_lightning():
    """Get lightning signals."""
    try:
        from app.services.hermes_strategies.lightning_v2 import LightningV2
        engine = _get_engine()
        data = engine.get_all_data() if engine else {}
        strategy = LightningV2()
        signals = strategy.generate(data)
        return jsonify({
            "ok": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
            "timestamp": _now(),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 16. Ambush ────────────────────────────────────────────────

@hermes_bp.route("/ambush", methods=["GET"])
def get_ambush():
    """Get ambush (埋伏) signals."""
    try:
        from app.services.hermes_strategies.ambush_v3 import AmbushV3
        engine = _get_engine()
        data = engine.get_all_data() if engine else {}
        strategy = AmbushV3()
        signals = strategy.generate(data)
        return jsonify({
            "ok": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
            "timestamp": _now(),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 17. Integration Status ────────────────────────────────────

@hermes_bp.route("/integration-status", methods=["GET"])
def get_integration_status():
    """Get QD integration status."""
    try:
        from app.services.hermes_strategies.hermes_qd_bridge import get_bridge_status, integrate_with_quantdinger
        status = get_bridge_status()
        return jsonify({"ok": True, "timestamp": _now(), **status})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 18. Tracker endpoints ─────────────────────────────────────

@hermes_bp.route("/tracker/status", methods=["GET"])
def get_tracker_status():
    try:
        tracker = _get_tracker()
        if tracker:
            return jsonify({"ok": True, "timestamp": _now(), **tracker.get_accuracy_stats()})
        return jsonify({"ok": True, "status": "not_running", "total": 0})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_bp.route("/tracker/active", methods=["GET"])
def get_tracker_active():
    try:
        tracker = _get_tracker()
        active = tracker.get_active() if tracker else []
        return jsonify({"ok": True, "count": len(active), "active": active})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_bp.route("/tracker/closed", methods=["GET"])
def get_tracker_closed():
    try:
        tracker = _get_tracker()
        limit = request.args.get("limit", 50, type=int)
        closed = tracker.get_closed(limit) if tracker else []
        return jsonify({"ok": True, "count": len(closed), "closed": closed})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

