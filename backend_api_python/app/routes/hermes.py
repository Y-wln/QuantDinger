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
        # Filter
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
        events = body.get("events", [])
        result = engine.score_coin(events)
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

    # Store or forward the signal
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
