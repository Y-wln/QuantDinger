# signal_tracker.py - logs every signal for accuracy calculation
# Add to yaobi_pusher.py: after push, call track_signal()

import json, os, time
from datetime import datetime, timezone, timedelta

LOG_PATH = "/home/ubuntu/scripts/agents/signal_log.json"
BJT = timezone(timedelta(hours=8))

def track_signals(signals):
    """Log signals to file for later accuracy verification."""
    entry = {
        "ts": time.time(),
        "time": datetime.now(BJT).strftime("%m/%d %H:%M:%S"),
        "signals": []
    }
    for s in signals:
        entry["signals"].append({
            "sym": s["sym"].replace("USDT", ""),
            "dir": s["dir"],
            "price": s["price"],
            "score": s["score"],
            "reasons": s.get("reasons", [])[:3]
        })
    
    existing = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                existing = json.load(f)
        except:
            pass
    
    existing.append(entry)
    
    # Keep last 500 entries
    if len(existing) > 500:
        existing = existing[-500:]
    
    with open(LOG_PATH, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=1)
    
    print("[Tracker] logged %d signals" % len(entry["signals"]))

def get_accuracy(hours=24):
    """Calculate accuracy by checking signal outcomes against current prices."""
    # This needs price verification - placeholder
    if not os.path.exists(LOG_PATH):
        return None
    with open(LOG_PATH) as f:
        data = json.load(f)
    
    cutoff = time.time() - hours * 3600
    recent = [e for e in data if e["ts"] > cutoff]
    
    total = sum(len(e["signals"]) for e in recent)
    longs = sum(1 for e in recent for s in e["signals"] if s["dir"]=="long")
    shorts = sum(1 for e in recent for s in e["signals"] if s["dir"]=="short")
    
    return {"total": total, "longs": longs, "shorts": shorts, "entries": len(recent)}
