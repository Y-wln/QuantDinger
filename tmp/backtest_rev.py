import sys, json, urllib.request, time
sys.path.insert(0,"/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines

coins = ["IOUSDT","ENAUSDT","TAOUSDT","PLAYUSDT","ONDOUSDT","STGUSDT","MEGAUSDT",
    "COAIUSDT","FETUSDT","WLDUSDT","TRUMPUSDT","AIOUSDT"]

def detect_reversal(k5):
    if not k5 or len(k5) < 15: return None
    vols = [float(k["v"]) for k in k5[-15:]]
    avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
    last_v = float(k5[-2]["v"])
    last_o = float(k5[-2]["o"]); last_c = float(k5[-2]["c"])
    last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
    curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
    curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
    
    if last_v > avg_v * 3 and last_chg > 1.5 and curr_chg < -0.2:
        return ("PUMP_SHORT", "short", min(int(last_v/avg_v * 6), 70))
    if len(k5) >= 6:
        cum = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-5,-2) if float(k5[i]["o"])>0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8,-5))
        vr = v3 / max(v3p, 0.001)
        if cum > 2.0 and vr > 3 and curr_chg < 0:
            return ("CUMUL_SHORT", "short", min(int(vr * 8), 70))
    if last_v > avg_v * 3 and last_chg < -1.5 and curr_chg > 0.2:
        return ("DUMP_LONG", "long", min(int(last_v/avg_v * 6), 70))
    if len(k5) >= 6:
        cum = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-5,-2) if float(k5[i]["o"])>0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8,-5))
        vr = v3 / max(v3p, 0.001)
        if cum < -2.0 and vr > 3 and curr_chg > 0:
            return ("CUMUL_LONG", "long", min(int(vr * 8), 70))
    return None

# Backtest: slide through last 2 hours of 5m candles (24 candles)
print("=== Sliding window backtest (last 24 candles, 5m) ===")
for sym in coins:
    try:
        k5 = fetch_klines(sym, "5m", 40)
        if not k5 or len(k5) < 20:
            print("%s: insufficient data" % sym)
            continue
        triggers = []
        for i in range(15, len(k5)):
            window = k5[:i+1]
            r = detect_reversal(window)
            if r:
                ptype, direction, score = r
                t = k5[i]["t"]
                triggers.append("%s %s score=%d @t=%d" % (direction, ptype, score, t))
        if triggers:
            print("%s: %d triggers:" % (sym, len(triggers)))
            for tr in triggers[-5:]:
                print("  ", tr)
        else:
            # Print best stats
            vols = [float(k["v"]) for k in k5[-24:]]
            avg_v = sum(vols)/len(vols)
            chgs = [(float(k["c"])-float(k["o"]))/float(k["o"])*100 for k in k5[-24:] if float(k["o"])>0]
            max_chg = max(chgs) if chgs else 0
            min_chg = min(chgs) if chgs else 0
            max_vr = max([v/avg_v for v in vols]) if avg_v > 0 else 0
            print("%s: NO triggers | max_chg=%.2f%% min_chg=%.2f%% max_vr=%.1fx" % (sym, max_chg, min_chg, max_vr))
    except Exception as e:
        print("%s: ERR - %s" % (sym, str(e)[:60]))