#!/usr/bin/env python3
"""Backtest demon_hunter logic on microcaps - last 24h"""
import sys, json, time
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines, calc_cvd

MICRO_CAPS = [
    "IOUSDT","ENAUSDT","TAOUSDT","ONDOUSDT","ALLOUSDT","TRUMPUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT",
    "COAIUSDT","MEGAUSDT","CHIPUSDT","ESPORTSUSDT","SENTUSDT",
    "JASMYUSDT","ALGOUSDT","JCTUSDT","WLDUSDT","FETUSDT",
    "HYPEUSDT","INJUSDT","APTUSDT","DASHUSDT","ZECUSDT"
]

def detect(k5):
    if not k5 or len(k5) < 12: return None
    vols = [float(k["v"]) for k in k5]
    avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
    if avg_v < 1: return None
    
    prev_o = float(k5[-2]["o"]); prev_c = float(k5[-2]["c"])
    prev_v = float(k5[-2]["v"])
    prev_chg = (prev_c - prev_o) / prev_o * 100 if prev_o > 0 else 0
    curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
    curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
    vr = prev_v / max(avg_v, 0.001)
    
    # PUMP -> SHORT
    if vr >= 2.0 and prev_chg >= 2.0 and curr_chg <= 0.1:
        score = min(int(vr * 8 + abs(prev_chg) * 3), 80)
        return ("short", score, prev_c)
    
    # Cumulative pump
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100 for i in range(-5,-2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8,-5))
        v3r = v3 / max(v3p, 0.001)
        if cum3 >= 3.0 and v3r >= 2.0 and curr_chg <= 0.2:
            score = min(int(v3r * 6 + cum3 * 3), 80)
            return ("short", score, prev_c)
    
    # DUMP -> LONG
    if vr >= 2.0 and prev_chg <= -2.0 and curr_chg >= -0.1:
        score = min(int(vr * 8 + abs(prev_chg) * 3), 80)
        return ("long", score, prev_c)
    
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100 for i in range(-5,-2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8,-5))
        v3r = v3 / max(v3p, 0.001)
        if cum3 <= -3.0 and v3r >= 2.0 and curr_chg >= -0.2:
            score = min(int(v3r * 6 + abs(cum3) * 3), 80)
            return ("long", score, prev_c)
    return None

print("=" * 50)
print("Demon Hunter Backtest | 27 microcaps | 24h")
print("=" * 50)

results = {"long": {"wins":0,"loss":0,"pnls":[]}, "short": {"wins":0,"loss":0,"pnls":[]}}
total_signals = 0
coins_with_signals = 0

for sym in MICRO_CAPS:
    try:
        k5 = fetch_klines(sym, "5m", 300)
        if not k5 or len(k5) < 30:
            continue
        
        coin_signals = 0
        for i in range(15, len(k5)-6):
            window = k5[:i+1]
            future = k5[i+6] if i+6 < len(k5) else k5[-1]
            
            r = detect(window)
            if r:
                direction, score, entry = r
                exit_p = float(future["c"])
                pnl = (exit_p - entry) / entry * 100 if direction == "long" else (entry - exit_p) / entry * 100
                if pnl > 0:
                    results[direction]["wins"] += 1
                else:
                    results[direction]["loss"] += 1
                results[direction]["pnls"].append(pnl)
                coin_signals += 1
                total_signals += 1
        
        if coin_signals > 0:
            coins_with_signals += 1
            print(".", end="", flush=True)
    except Exception as e:
        print("E", end="", flush=True)

print("\n")
for d in ["long", "short"]:
    r = results[d]
    t = r["wins"] + r["loss"]
    if t > 0:
        wr = r["wins"] / t * 100
        avg_pnl = sum(r["pnls"]) / len(r["pnls"])
        best = max(r["pnls"])
        worst = min(r["pnls"])
        print("%s: W%d L%d = %.0f%% | avg: %+.2f%% | best: %+.2f%% | worst: %+.2f%% | N=%d" % (d, r["wins"], r["loss"], wr, avg_pnl, best, worst, t))

all_w = sum(r["wins"] for r in results.values())
all_l = sum(r["loss"] for r in results.values())
if all_w + all_l > 0:
    print("COMBINED: %.0f%% | %d signals | %d coins active" % (all_w/(all_w+all_l)*100, total_signals, coins_with_signals))