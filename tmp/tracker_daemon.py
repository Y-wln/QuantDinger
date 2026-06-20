#!/usr/bin/env python3
"""tracker_daemon.py - Standalone tracking engine, zero coupling with strategy"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_tracker import load, save, check_results, calc_stats, indicator_stats
from hermes_core import fetch_price, feishu_send

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "agent_position.json")
PIPELINE_FILE = os.path.join(os.path.dirname(__file__), "pipeline_tracker.json")
STATS_INTERVAL = 3600
REPORT_INTERVAL = 21600

_last_stats = 0
_last_report = 0

def load_positions():
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("positions", {})
    except:
        return {}

def build_pipeline():
    data = load()
    positions = load_positions()
    pipeline = {"signals": {}, "updated": time.time()}
    
    for sig in data.get("signals", []):
        sid = sig.get("id", "")
        sym = sig.get("symbol", "")
        extras = sig.get("extras", {})
        
        entry = {
            "id": sid,
            "symbol": sym,
            "direction": sig.get("direction", "?"),
            "raw": {
                "score": sig.get("score", 0),
                "price": sig.get("entry_price", 0),
                "ts": sig.get("timestamp", 0),
            },
        }
        
        if extras.get("triggers") or extras.get("fast_votes"):
            entry["confirm"] = {
                "fast_votes": extras.get("fast_votes", 0),
                "confirmed": extras.get("confirmed", False),
                "triggers": extras.get("triggers", [])[:5],
            }
        
        decision = extras.get("decision", "")
        if decision and decision not in ("open", "no_decision", "pending_open"):
            entry["filter"] = {"passed": False, "reason": decision}
            entry["decision"] = decision
        elif decision in ("open", "pending_open"):
            entry["filter"] = {"passed": True}
            entry["decision"] = "open"
        
        indicators = extras.get("indicators", {})
        if indicators:
            entry["indicators"] = indicators
        
        pos_key = sym + "USDT"
        if pos_key in positions:
            pos = positions[pos_key]
            entry["opened"] = {
                "entry_price": pos.get("entry_price"),
                "sl": pos.get("sl"),
                "tp": pos.get("tp"),
                "cascade": pos.get("cascade", 1),
                "size_pct": pos.get("size_pct", 1.0),
            }
        
        outcome = sig.get("outcome")
        if outcome:
            entry["closed"] = {
                "exit_price": outcome.get("exit_price"),
                "pnl_pct": outcome.get("pnl_pct"),
                "reason": outcome.get("exit_reason", ""),
            }
            entry["settled"] = True
        
        results = sig.get("results", {})
        for h in ["4h", "12h", "24h"]:
            if h in results:
                r = results[h]
                entry[f"verify_{h}"] = {
                    "price": r.get("price"),
                    "change_pct": r.get("change_pct"),
                    "correct": r.get("correct"),
                }
        
        pipeline["signals"][sid] = entry
    
    with open(PIPELINE_FILE, "w") as f:
        json.dump(pipeline, f, indent=2, default=str, ensure_ascii=False)
    
    return pipeline

def main():
    global _last_stats, _last_report
    print("[tracker_daemon] v1 started - zero coupling, reads JSON only")
    
    while True:
        try:
            stats = check_results(fetch_price)
            pipeline = build_pipeline()
            sigs = pipeline.get("signals", {})
            
            now = time.time()
            if now - _last_stats > STATS_INTERVAL:
                ind_stats = indicator_stats()
                if ind_stats:
                    top5 = list(ind_stats.items())[:5]
                    lines = ["[Indicator Accuracy top5]"]
                    for name, s in top5:
                        lines.append(f"  {name}: {s['wr']}% ({s['correct']}/{s['total']})")
                    print("\n".join(lines))
                _last_stats = now
            
            if now - _last_report > REPORT_INTERVAL:
                data = load()
                summary = calc_stats(data["signals"])
                wr = summary.get("win_rate", 0)
                total = summary.get("total", 0)
                feishu_send(f"[Tracker] {total} signals settled | WR:{wr}%")
                _last_report = now
            
            n_total = len(sigs)
            n_confirm = sum(1 for s in sigs.values() if "confirm" in s)
            n_opened = sum(1 for s in sigs.values() if "opened" in s)
            n_closed = sum(1 for s in sigs.values() if "closed" in s)
            print(f"  [{time.strftime('%H:%M')}] sigs:{n_total} conf:{n_confirm} open:{n_opened} closed:{n_closed}")
            
        except Exception as e:
            print(f"  [tracker error] {e}")
        
        time.sleep(60)

if __name__ == "__main__":
    main()
