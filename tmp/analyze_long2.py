import sys
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

# Collect longs with rich features
longs = []
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
            
            found = None; best_score = 0
            if vr >= 2.0 and p_chg <= -2.0 and c_chg >= -0.2:
                s = min(int(vr * 7 + abs(p_chg) * 3), 70)
                found = ("DUMP1C", s, p_c); best_score = s
            if len(window) >= 8:
                cum3 = sum((float(window[i2]["c"]) - float(window[i2]["o"])) / float(window[i2]["o"]) * 100 for i2 in range(-5,-2) if float(window[i2]["o"]) > 0)
                v3 = sum(float(window[i2]["v"]) for i2 in range(-5,-2))
                v3p = sum(float(window[i2]["v"]) for i2 in range(-8,-5))
                v3r = v3 / max(v3p, 0.001)
                if cum3 <= -3.0 and v3r >= 1.8 and c_chg >= -0.3:
                    s = min(int(v3r * 5 + abs(cum3) * 3), 65)
                    if s > best_score: found = ("DUMP3C", s, p_c); best_score = s
            if vwap_dev < -5.0 and c_chg >= -0.3:
                s = min(int(abs(vwap_dev) * 5), 60)
                if s > best_score: found = ("VWAP_LO", s, p_c); best_score = s
            
            if found:
                ptype, score, entry = found
                exit_p = float(k5[i+6]["c"]) if i+6 < len(k5) else float(k5[-1]["c"])
                pnl = (exit_p - entry) / entry * 100
                win = pnl > 0
                cv5 = calc_cvd(window, 3)
                red_cnt = sum(1 for i2 in range(-5, 0) if float(window[i2]["c"]) < float(window[i2]["o"]))
                cum5 = sum((float(window[i2]["c"]) - float(window[i2]["o"])) / float(window[i2]["o"]) * 100 for i2 in range(-5, 0) if float(window[i2]["o"]) > 0)
                
                longs.append({
                    "win": win, "pnl": pnl, "type": ptype, "vr": vr,
                    "chg": abs(p_chg), "vwap_dev": abs(vwap_dev) if vwap_dev < 0 else 0,
                    "cv5": cv5, "red_cnt": red_cnt, "cum5": cum5, "score": score
                })
    except: pass

print("Total:", len(longs))

# Test different combined filters
filters = [
    ("dump>=4%% AND score>=45", lambda l: l["chg"] >= 4 and l["score"] >= 45),
    ("dump>=5%%", lambda l: l["chg"] >= 5),
    ("score>=50", lambda l: l["score"] >= 50),
    ("dump>=4%% AND VR>=4", lambda l: l["chg"] >= 4 and l["vr"] >= 4),
    ("(dump>=5%%) OR (score>=55)", lambda l: l["chg"] >= 5 or l["score"] >= 55),
    ("dump>=4%% AND cv5>=10 AND red<=4", lambda l: l["chg"] >= 4 and l["cv5"] >= 10 and l["red_cnt"] <= 4),
    ("dump>=3%% AND VR>=3 AND score>=40", lambda l: l["chg"] >= 3 and l["vr"] >= 3 and l["score"] >= 40),
    ("VWAP_LO AND vwap>=7%%", lambda l: l["type"] == "VWAP_LO" and l["vwap_dev"] >= 7),
]

print("\nFilter performance:")
for name, fn in filters:
    subset = [l for l in longs if fn(l)]
    if subset:
        wins = sum(1 for l in subset if l["win"])
        avg = sum(l["pnl"] for l in subset) / len(subset)
        best = max(l["pnl"] for l in subset)
        print("  %s: %d sigs, %.0f%% win, avg %+.2f%%, best %+.2f%%" % (name, len(subset), wins/len(subset)*100, avg, best))