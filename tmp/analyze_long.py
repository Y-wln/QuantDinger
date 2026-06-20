import sys, json
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

# Collect ALL long signals with detailed features
longs = []  # (win, pnl, features_dict)

for sym in COINS:
    try:
        k5 = fetch_klines(sym, "5m", 300)
        if not k5 or len(k5) < 30: continue
        for i in range(15, len(k5)-6):
            window = k5[:i+1]
            if len(window) < 12: continue
            vols = [float(k["v"]) for k in window]
            avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
            price = float(window[-1]["c"])
            vwap = calc_vwap(window)
            vwap_dev = (price - vwap) / vwap * 100 if vwap > 0 else 0
            p_o = float(window[-2]["o"]); p_c = float(window[-2]["c"]); p_v = float(window[-2]["v"])
            p_chg = (p_c - p_o) / p_o * 100 if p_o > 0 else 0
            c_o = float(window[-1]["o"]); c_c = float(window[-1]["c"])
            c_chg = (c_c - c_o) / c_o * 100 if c_o > 0 else 0
            vr = p_v / max(avg_v, 0.001)
            
            # Only LONG signals
            found = None
            if vr >= 2.0 and p_chg <= -2.0 and c_chg >= -0.2:
                found = ("DUMP1C", min(int(vr * 7 + abs(p_chg) * 3), 70), p_c)
            if len(window) >= 8 and not found:
                cum3 = sum((float(window[i2]["c"]) - float(window[i2]["o"])) / float(window[i2]["o"]) * 100 for i2 in range(-5,-2) if float(window[i2]["o"]) > 0)
                v3 = sum(float(window[i2]["v"]) for i2 in range(-5,-2))
                v3p = sum(float(window[i2]["v"]) for i2 in range(-8,-5))
                v3r = v3 / max(v3p, 0.001)
                if cum3 <= -3.0 and v3r >= 1.8 and c_chg >= -0.3:
                    found = ("DUMP3C", min(int(v3r * 5 + abs(cum3) * 3), 65), p_c)
            if not found and vwap_dev < -5.0 and c_chg >= -0.3:
                found = ("VWAP_LO", min(int(abs(vwap_dev) * 5), 60), p_c)
            
            if found:
                ptype, score, entry = found
                exit_p = float(k5[i+6]["c"]) if i+6 < len(k5) else float(k5[-1]["c"])
                pnl = (exit_p - entry) / entry * 100
                win = pnl > 0
                
                # Features that might predict win
                cv5 = calc_cvd(window, 3)
                # Count red candles in last 5
                red_cnt = sum(1 for i2 in range(-5, 0) if float(window[i2]["c"]) < float(window[i2]["o"]))
                # Cumulative dump %
                cum5 = sum((float(window[i2]["c"]) - float(window[i2]["o"])) / float(window[i2]["o"]) * 100 for i2 in range(-5, 0) if float(window[i2]["o"]) > 0)
                
                longs.append({
                    "win": win, "pnl": pnl, "type": ptype,
                    "vr": vr, "chg": abs(p_chg), "vwap_dev": abs(vwap_dev) if vwap_dev < 0 else 0,
                    "cv5": cv5, "red_cnt": red_cnt, "cum5": cum5,
                    "score": score
                })
    except: pass

print("Total long signals:", len(longs))
print()

# Analyze by signal type
for ptype in ["DUMP1C", "DUMP3C", "VWAP_LO"]:
    subset = [l for l in longs if l["type"] == ptype]
    if subset:
        wins = sum(1 for l in subset if l["win"])
        avg_pnl = sum(l["pnl"] for l in subset) / len(subset)
        print("%s: %d signals, %.0f%% win, avg pnl %+.2f%%" % (ptype, len(subset), wins/len(subset)*100, avg_pnl))

print()

# Analyze by features
print("=== Win rate by VR (vol ratio) ===")
for thresh in [2, 3, 4, 6, 10]:
    subset = [l for l in longs if l["vr"] >= thresh]
    if subset:
        wins = sum(1 for l in subset if l["win"])
        print("  VR>=%d: %d signals, %.0f%% win" % (thresh, len(subset), wins/len(subset)*100))

print("\n=== Win rate by dump size ===")
for thresh in [1, 2, 3, 5, 8]:
    subset = [l for l in longs if l["chg"] >= thresh]
    if subset:
        wins = sum(1 for l in subset if l["win"])
        print("  dump>=%d%%: %d signals, %.0f%% win" % (thresh, len(subset), wins/len(subset)*100))

print("\n=== Win rate by CVD exhaustion ===")
for thresh in [-20, -10, 0, 10, 20]:
    subset = [l for l in longs if l["cv5"] >= thresh]
    if subset:
        wins = sum(1 for l in subset if l["win"])
        print("  CVD>=%d: %d signals, %.0f%% win" % (thresh, len(subset), wins/len(subset)*100))

print("\n=== Win rate by red candle count ===")
for thresh in [2, 3, 4, 5]:
    subset = [l for l in longs if l["red_cnt"] >= thresh]
    if subset:
        wins = sum(1 for l in subset if l["win"])
        print("  red>=%d: %d signals, %.0f%% win" % (thresh, len(subset), wins/len(subset)*100))

print("\n=== Win rate by score ===")
for thresh in [20, 30, 40, 50, 60]:
    subset = [l for l in longs if l["score"] >= thresh]
    if subset:
        wins = sum(1 for l in subset if l["win"])
        print("  score>=%d: %d signals, %.0f%% win" % (thresh, len(subset), wins/len(subset)*100))

# Combined: VR>=4 AND dump>=3% AND CVD>=10
subset = [l for l in longs if l["vr"] >= 4 and l["chg"] >= 3 and l["cv5"] >= 10]
if subset:
    wins = sum(1 for l in subset if l["win"])
    avg = sum(l["pnl"] for l in subset) / len(subset)
    print("\n=== HIGH CONFIDENCE (VR>=4, dump>=3%, CVD>=10) ===")
    print("%d signals, %.0f%% win, avg pnl %+.2f%%" % (len(subset), wins/len(subset)*100, avg))