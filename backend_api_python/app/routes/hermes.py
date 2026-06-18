"""
Hermes Signal Routes.
Exposes Mercu.win derived signals via REST API.
"""
from flask import jsonify, request
from app.openapi.blueprint import HumanBlueprint as Blueprint

hermes_blp = Blueprint("hermes", __name__)


@hermes_blp.route("/signals", methods=["GET"])
def get_hermes_signals():
    """Get current Hermes/Mercu trading signals."""
    from app.data_providers.hermes_mercu import get_hermes_engine
    engine = get_hermes_engine()
    try:
        limit = request.args.get("limit", 20, type=int)
        min_score = request.args.get("min_score", 5, type=int)
        signals = engine.generate_signals()
        signals = [s for s in signals if abs(s["score"]) >= min_score]
        return jsonify({
            "ok": True,
            "count": len(signals[:limit]),
            "signals": signals[:limit],
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/data", methods=["GET"])
def get_hermes_raw_data():
    """Get raw Mercu data (anomalies, momentum, surge)."""
    from app.data_providers.hermes_mercu import get_hermes_engine
    engine = get_hermes_engine()
    try:
        data = engine.get_all_data()
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/score", methods=["POST"])
def score_hermes_coin():
    """Score a coin from posted state events."""
    from app.data_providers.hermes_mercu import get_hermes_engine
    engine = get_hermes_engine()
    try:
        body = request.get_json(silent=True) or {}
        symbol = body.get("symbol", "")
        events = body.get("events", [])
        result = engine.score_events(symbol, events)
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/push", methods=["POST"])
def push_hermes_signal():
    """Receive signals from Hermes daemon (push integration)."""
    body = request.get_json(silent=True) or {}
    symbol = body.get("symbol", "")
    direction = body.get("direction", "LONG")
    score = body.get("score", 0)
    stage = body.get("stage", "")
    details = body.get("details", [])

    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info(f"Received Hermes signal: {symbol} {direction} score={score} stage={stage}")

    return jsonify({
        "ok": True,
        "received": {
            "symbol": symbol,
            "direction": direction,
            "score": score,
            "stage": stage,
        }
    })


@hermes_blp.route("/status", methods=["GET"])
def get_hermes_status():
    """Get Hermes strategy service status."""
    try:
        from app.services.hermes_strategy_service import get_hermes_strategy_service
        svc = get_hermes_strategy_service()
        return jsonify({"ok": True, "status": svc.get_status()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/dashboard", methods=["GET"])
def get_hermes_dashboard():
    """Get Hermes dashboard metrics."""
    try:
        from app.services.hermes_integration import hermes_get_dashboard_metrics
        metrics = hermes_get_dashboard_metrics()
        return jsonify({"ok": True, "metrics": metrics})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/backtest-data", methods=["GET"])
def get_hermes_backtest_data():
    """Get Hermes signal history formatted for backtesting."""
    try:
        from app.services.hermes_strategy_service import get_hermes_strategy_service
        from app.services.hermes_integration import hermes_prepare_backtest_data
        svc = get_hermes_strategy_service()
        data = hermes_prepare_backtest_data(svc._signal_history)
        return jsonify({"ok": True, "count": len(data), "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



@hermes_blp.route("/backtest-accuracy", methods=["GET"])
def get_hermes_backtest_accuracy():
    """Run accuracy analysis on historical Hermes signals."""
    try:
        from app.services.hermes_strategy_service import get_hermes_strategy_service
        from app.services.hermes_backtest import get_hermes_backtest_bridge
        svc = get_hermes_strategy_service()
        bridge = get_hermes_backtest_bridge()
        signals = svc._signal_history
        if not signals:
            return jsonify({"ok": False, "error": "No signal history available"}), 404
        limit = request.args.get("limit", 100, type=int)
        report = bridge.quick_accuracy_report(signals[-limit:])
        return jsonify({"ok": True, "report": report, "signal_count": len(signals[-limit:])})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# Scanner routes (yaobi, lightning, ambush)
# ============================================================

@hermes_blp.route("/yaobi", methods=["GET"])
def get_yaobi_signals():
    """Get yaobi (demon coin) scanner signals."""
    try:
        from app.services.yaobi_scanner import get_yaobi_scanner
        scanner = get_yaobi_scanner()
        limit = request.args.get("limit", 10, type=int)
        direction = request.args.get("direction", None)
        results = scanner.get_top(limit, direction)
        return jsonify({"ok": True, "count": len(results), "signals": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/yaobi/scan", methods=["POST"])
def trigger_yaobi_scan():
    """Trigger a yaobi scan."""
    try:
        from app.services.yaobi_scanner import get_yaobi_scanner
        scanner = get_yaobi_scanner()
        results = scanner.scan()
        return jsonify({"ok": True, "count": len(results), "signals": [r.to_dict() for r in results[:20]]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/lightning", methods=["GET"])
def get_lightning_signals():
    """Get lightning (volume burst) signals."""
    try:
        from app.services.lightning_scanner import get_lightning_scanner
        scanner = get_lightning_scanner()
        limit = request.args.get("limit", 10, type=int)
        return jsonify({"ok": True, "signals": scanner.get_recent(limit)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/ambush", methods=["GET"])
def get_ambush_signals():
    """Get ambush (pre-positioning) signals."""
    try:
        from app.services.ambush_scanner import get_ambush_scanner
        scanner = get_ambush_scanner()
        limit = request.args.get("limit", 10, type=int)
        return jsonify({"ok": True, "signals": scanner.get_recent(limit)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# Tracker routes
# ============================================================

@hermes_blp.route("/tracker/status", methods=["GET"])
def get_tracker_status():
    """Get pipeline tracker status and accuracy."""
    try:
        from app.services.pipeline_tracker import get_pipeline_tracker
        tracker = get_pipeline_tracker()
        return jsonify({"ok": True, "status": tracker.get_status()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/tracker/active", methods=["GET"])
def get_tracker_active():
    """Get active tracked signals."""
    try:
        from app.services.pipeline_tracker import get_pipeline_tracker
        tracker = get_pipeline_tracker()
        return jsonify({"ok": True, "signals": tracker.get_active()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/tracker/closed", methods=["GET"])
def get_tracker_closed():
    """Get closed tracked signals."""
    try:
        from app.services.pipeline_tracker import get_pipeline_tracker
        tracker = get_pipeline_tracker()
        limit = request.args.get("limit", 50, type=int)
        return jsonify({"ok": True, "signals": tracker.get_closed(limit)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# SelfCheck route
# ============================================================

@hermes_blp.route("/health", methods=["GET"])
def get_hermes_health():
    """Get full system health check."""
    try:
        from app.services.selfcheck import get_selfcheck
        checker = get_selfcheck()
        results = checker.run_check()
        return jsonify({"ok": True, "health": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@hermes_blp.route("/integration-status", methods=["GET"])
def get_hermes_integration_status():
    """Get Hermes-QuantDinger integration status."""
    try:
        from app.services.hermes_integration import integrate_hermes_with_quantdinger
        status = integrate_hermes_with_quantdinger()
        return jsonify({"ok": True, "integration": status})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


