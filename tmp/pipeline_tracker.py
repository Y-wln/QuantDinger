# Pipeline Tracker - 6-stage camera recording entire strategy journey
import json, os, time
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
TRACK_FILE = "/home/ubuntu/scripts/agents/pipeline_tracker.json"

def _load():
    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"runs": [], "signals": {}}

def _save(data):
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

def stage_raw(signal_id, sig):
    data = _load()
    entry = data["signals"].setdefault(signal_id, {
        "id": signal_id,
        "symbol": sig.get("symbol", "?").replace("USDT", ""),
        "direction": sig.get("signal", "?"),
        "first_seen": time.time(),
    })
    entry["raw"] = {
        "score": sig.get("score", 0),
        "price": sig.get("price", 0),
        "cvd1h": sig.get("cvd1h", 0),
        "fast_signal": sig.get("fast_signal", "wait"),
        "ts": time.time(),
    }
    _save(data)

def stage_confirm(signal_id, sig):
    data = _load()
    entry = data["signals"].setdefault(signal_id, {
        "id": signal_id,
        "symbol": sig.get("symbol", "?").replace("USDT", ""),
        "direction": sig.get("signal", "?"),
    })
    entry["confirm"] = {
        "fast_votes": sig.get("fast_votes", 0),
        "confirmed": sig.get("confirmed", False),
        "leading_bonus": sig.get("leading_bonus", 0),
        "triggers": sig.get("leading_reasons", [])[:5],
        "ts": time.time(),
    }
    _save(data)

def stage_filter(signal_id, passed, reason=None, checks=None):
    data = _load()
    entry = data["signals"].setdefault(signal_id, {})
    entry.setdefault("id", signal_id)
    entry["filter"] = {
        "passed": passed,
        "reason": reason,
        "checks": checks or {},
        "ts": time.time(),
    }
    _save(data)

def stage_scored(signal_id, final_score, adjustments, indicators=None):
    data = _load()
    entry = data["signals"].setdefault(signal_id, {})
    entry.setdefault("id", signal_id)
    entry["scored"] = {
        "final_score": final_score,
        "adjustments": adjustments,
        "indicators": indicators or {},
        "ts": time.time(),
    }
    _save(data)

def stage_opened(signal_id, entry_price, sl, tp, cascade, size_pct):
    data = _load()
    entry = data["signals"].setdefault(signal_id, {})
    entry.setdefault("id", signal_id)
    entry["opened"] = {
        "entry_price": entry_price,
        "sl": sl,
        "tp": tp,
        "cascade": cascade,
        "size_pct": size_pct,
        "ts": time.time(),
    }
    entry["settled"] = False
    _save(data)

def stage_closed(signal_id, exit_price, pnl_pct, reason):
    data = _load()
    entry = data["signals"].setdefault(signal_id, {})
    entry.setdefault("id", signal_id)
    entry["closed"] = {
        "exit_price": exit_price,
        "pnl_pct": round(pnl_pct, 4),
        "reason": reason,
        "ts": time.time(),
    }
    entry["settled"] = True
    _save(data)

def stage_decision(signal_id, decision):
    data = _load()
    entry = data["signals"].setdefault(signal_id, {})
    entry.setdefault("id", signal_id)
    entry["decision"] = decision
    _save(data)

def get_pipeline(signal_id):
    data = _load()
    return data["signals"].get(signal_id, data["signals"].get(str(signal_id)))

def stats():
    data = _load()
    sigs = data["signals"]
    total = len(sigs)
    return {
        "total": total,
        "stage_raw": sum(1 for s in sigs.values() if "raw" in s),
        "stage_confirm": sum(1 for s in sigs.values() if "confirm" in s),
        "stage_filter": sum(1 for s in sigs.values() if "filter" in s),
        "stage_scored": sum(1 for s in sigs.values() if "scored" in s),
        "stage_opened": sum(1 for s in sigs.values() if "opened" in s),
        "stage_closed": sum(1 for s in sigs.values() if "closed" in s),
    }

print("[pipeline_tracker] v1 - 6-stage camera loaded")
