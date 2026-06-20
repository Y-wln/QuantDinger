import sys, json, time
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines, calc_cvd

COINS = [
    "IOUSDT","ENAUSDT","TAOUSDT","ONDOUSDT","ALLOUSDT","TRUMPUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT",
    "COAIUSDT","MEGAUSDT","CHIPUSDT","ESPORTSUSDT","SENTUSDT",
    "JASMYUSDT","ALGOUSDT","FETUSDT","WLDUSDT","HYPEUSDT",
    "INJUSDT","APTUSDT","DASHUSDT","ZECUSDT","AAVEUSDT","JCTUSDT"
]

def calc_vwap(k5):
    if not k5: return 0
    total_pv = 0; total_v = 0
    for k in k5[-24:]:
        v = float(k["v"])
        typical = (float(k["h"]) + float(k["l"]) + float(k["c"])) / 3
        total_pv += typical * v
        total_v += v
    return total_pv / total_v if total_v > 0 else 0

def detect(k5):
    if not k5 or len(k5) < 12: return None
    vols = [float(k["v"]) for k in k5]
    avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
    if avg_v < 1: return None
    price = float(k5[-1]["c"])
    vwap = calc_vwap(k5)
    vwap_dev = (price - vwap) / vwap * 100 if vwap > 0 else 0
    p_o = float(k5[-2]["o"]); p_c = float(k5[-2]["c"]); p_v = float(k5[-2]["v"])
    p_chg = (p_c - p_o) / p_o * 100 if p_o > 0 else 0
    c_o = float(k5[-1]["o"]); c_c = float(k5[-1]["c"])
    c_chg = (c_c - c_o) / c_o * 100 if c_o > 0 else 0
    vr = p_v / max(avg_v, 0.001)
    best = None; best_score = 0
    # SHORT patterns
    if vr >= 2.0 and p_chg >= 2.0 and c_chg <= 0.2:
        s = min(int(vr * 7 + p_chg * 3), 70)
        if s > best_score: best = ("short", s, p_c); best_score = s
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100 for i in range(-5,-2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8,-5))
        v3r = v3 / max(v3p, 0.001)
        if cum3 >= 3.0 and v3r >= 1.8 and c_chg <= 0.3:
            s = min(int(v3r * 5 + cum3 * 3), 65)
            if s > best_score: best = ("short", s, p_c); best_score = s
    if vwap_dev > 5.0 and c_chg <= 0.3:
        s = min(int(vwap_dev * 5), 60)
        if s > best_score: best = ("short", s, p_c); best_score = s
    # LONG patterns
    if vr >= 2.0 and p_chg <= -2.0 and c_chg >= -0.2:
        s = min(int(vr * 7 + abs(p_chg) * 3), 70)
        if s > best_score: best = ("long", s, p_c); best_score = s
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100 for i in range(-5,-2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8,-5))
        v3r = v3 / max(v3p, 0.001)
        if cum3 <= -3.0 and v3r >= 1.8 and c_chg >= -0.3:
            s = min(int(v3r * 5 + abs(cum3) * 3), 65)
            if s > best_score: best = ("long", s, p_c); best_score = s
    if vwap_dev < -5.0 and c_chg >= -0.3:
        s = min(int(abs(vwap_dev) * 5), 60)
        if s > best_score: best = ("long", s, p_c); best_score = s
    return best

print("=" * 50)
print("Demon V2 Backtest | 27 microcaps | 24h")
print("=" * 50)

results = {"long": {"wins":0,"loss":0,"pnls":[]}, "short": {"wins":0,"loss":0,"pnls":[]}}
total = 0
for sym in COINS:
    try:
        k5 = fetch_klines(sym, "5m", 300)
        if not k5 or len(k5) < 30: continue
        for i in range(15, len(k5)-6):
            r = detect(k5[:i+1])
            if r:
                direction, score, entry = r
                exit_p = float(k5[i+6]["c"]) if i+6 < len(k5) else float(k5[-1]["c"])
                pnl = (exit_p - entry) / entry * 100 if direction == "long" else (entry - exit_p) / entry * 100
                if pnl > 0: results[direction]["wins"] += 1
                else: results[direction]["loss"] += 1
                results[direction]["pnls"].append(pnl)
                total += 1
        print(".", end="", flush=True)
    except: print("E", end="", flush=True)

print("\n")
for d in ["long", "short"]:
    r = results[d]; t = r["wins"] + r["loss"]
    if t > 0:
        wr = r["wins"] / t * 100
        avg = sum(r["pnls"]) / len(r["pnls"])
        best = max(r["pnls"]); worst = min(r["pnls"])
        print("%s: W%d L%d = %.0f%% | avg: %+.2f%% | best: %+.2f%% | worst: %+.2f%% | N=%d" % (d, r["wins"], r["loss"], wr, avg, best, worst, t))
all_w = sum(r["wins"] for r in results.values())
all_l = sum(r["loss"] for r in results.values())
print("COMBINED: %.0f%% | %d signals" % (all_w/(all_w+all_l)*100, total))