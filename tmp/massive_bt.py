#!/usr/bin/env python3
"""Massive backtest: reversal + acceleration across 30+ coins, last 24h"""
import sys, json, urllib.request, time
sys.path.insert(0,"/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","LTCUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
    "IOUSDT","ENAUSDT","TAOUSDT","ONDOUSDT","ALLOUSDT","NEARUSDT","INJUSDT","APTUSDT",
    "FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT",
    "MEGAUSDT","CHIPUSDT","ESPORTSUSDT","JASMYUSDT","ALGOUSDT"]

def detect_reversal(k5):
    """Mean-reversion: extreme move -> reversal detection"""
    if not k5 or len(k5) < 15: return None
    vols = [float(k["v"]) for k in k5]
    avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
    last_v = float(k5[-2]["v"])
    last_o = float(k5[-2]["o"]); last_c = float(k5[-2]["c"])
    last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
    curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
    curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
    
    # Pump -> Short
    if last_v > avg_v * 2 and last_chg > 1.0 and curr_chg < 0:
        score = min(int(last_v/avg_v * 5), 60)
        return ("PUMP_SHORT", "short", score, last_c)
    
    # Dump -> Long
    if last_v > avg_v * 2 and last_chg < -1.0 and curr_chg > 0:
        score = min(int(last_v/avg_v * 5), 60)
        return ("DUMP_LONG", "long", score, last_c)
    
    # Cumulative pump -> short
    if len(k5) >= 6:
        cum = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-5,-2) if float(k5[i]["o"])>0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8,-5))
        vr = v3 / max(v3p, 0.001)
        if cum > 1.5 and vr > 2 and curr_chg < 0:
            return ("CUMUL_SHORT", "short", min(int(vr*5), 60), last_c)
        if cum < -1.5 and vr > 2 and curr_chg > 0:
            return ("CUMUL_LONG", "long", min(int(vr*5), 60), last_c)
    return None

def detect_surge(k5):
    """Acceleration: vol spike -> trend continuation"""
    if not k5 or len(k5) < 15: return None
    vols = [float(k["v"]) for k in k5]
    avg_v = sum(vols[:-5]) / max(len(vols)-5, 1)
    recent_v = sum(vols[-3:]) / 3
    vr = recent_v / max(avg_v, 0.001)
    
    if vr < 2.0: return None
    
    last_c = float(k5[-1]["c"])
    # Check recent price direction
    chg_3 = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-3,0) if float(k5[i]["o"])>0)
    
    if chg_3 > 0.3:
        return ("MOMENTUM_UP", "long", min(int(vr*5), 60), last_c)
    elif chg_3 < -0.3:
        return ("MOMENTUM_DN", "short", min(int(vr*5), 60), last_c)
    return None

print("=" * 60)
print("Massive Backtest: Reversal + Surge | Last 24h | 35 coins")
print("=" * 60)

rev_results = {"long": {"wins":0,"loss":0,"pnls":[]}, "short": {"wins":0,"loss":0,"pnls":[]}}
srg_results = {"long": {"wins":0,"loss":0,"pnls":[]}, "short": {"wins":0,"loss":0,"pnls":[]}}

for sym in COINS:
    try:
        k5 = fetch_klines(sym, "5m", 300)  # Last ~24h
        if not k5 or len(k5) < 30:
            continue
        
        # Slide through all windows
        for i in range(20, len(k5)-6):
            window = k5[:i+1]
            future = k5[i+6] if i+6 < len(k5) else k5[-1]  # ~30min later
            
            # Reversal check
            r = detect_reversal(window)
            if r:
                ptype, direction, score, entry = r
                exit_p = float(future["c"])
                pnl = (exit_p - entry) / entry * 100 if direction == "long" else (entry - exit_p) / entry * 100
                if pnl > 0:
                    rev_results[direction]["wins"] += 1
                else:
                    rev_results[direction]["loss"] += 1
                rev_results[direction]["pnls"].append(pnl)
            
            # Surge check
            s = detect_surge(window)
            if s:
                ptype, direction, score, entry = s
                exit_p = float(future["c"])
                pnl = (exit_p - entry) / entry * 100 if direction == "long" else (entry - exit_p) / entry * 100
                if pnl > 0:
                    srg_results[direction]["wins"] += 1
                else:
                    srg_results[direction]["loss"] += 1
                srg_results[direction]["pnls"].append(pnl)
        
        print(".", end="", flush=True)
    except Exception as e:
        print("E(%s)" % sym[:4], end="", flush=True)

print("\n")
for name, results in [("REVERSAL", rev_results), ("SURGE/MOMENTUM", srg_results)]:
    print("=" * 40)
    print("  %s" % name)
    for d in ["long", "short"]:
        r = results[d]
        total = r["wins"] + r["loss"]
        if total > 0:
            wr = r["wins"] / total * 100
            avg_pnl = sum(r["pnls"]) / len(r["pnls"]) if r["pnls"] else 0
            print("  %s: W%d L%d = %.0f%% | avg pnl: %+.2f%% | signals: %d" % (d, r["wins"], r["loss"], wr, avg_pnl, total))
        else:
            print("  %s: no signals" % d)
    # Combined
    all_w = sum(r["wins"] for r in results.values())
    all_l = sum(r["loss"] for r in results.values())
    if all_w + all_l > 0:
        print("  COMBINED: W%d L%d = %.0f%% | total: %d" % (all_w, all_l, all_w/(all_w+all_l)*100, all_w+all_l))