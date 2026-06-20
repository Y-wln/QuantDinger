# reversal_hunter.py v1 - mean-reversion strategy
# Extreme pump -> short, extreme dump -> long
# The opposite of trend-following

import sys, os, time, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import (fetch_klines, fetch_price, fetch_orderbook_imbalance,
                         feishu_app_send, calc_cvd)
from signal_tracker import track_signals
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BJT = timezone(timedelta(hours=8))
CHAT_ID = "oc_58c90b36ddb0d64439c64ed83a16b47b"

COINS = ["CHZUSDT","IOUSDT","SENTUSDT","ENAUSDT","UNIUSDT",
    "TAOUSDT","ONDOUSDT","ALLOUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT",
    "MEGAUSDT","CHIPUSDT","KAITOUSDT","ESPORTSUSDT","MITOUSDT","SIRENUSDT"]

_cooldown = {}  # sym -> last push time

print("[Reversal v1] Mean-reversion hunter starting...")
feishu_app_send("Reversal Hunter v1 | pump->short dump->long | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

def detect_reversal(k5, k1m=None):
    """Detect extreme moves ripe for reversal.
    Returns (signal_type, direction, score, reasons) or None.
    """
    if not k5 or len(k5) < 20: return None
    
    vols = [float(k["v"]) for k in k5[-20:]]
    avg_v = sum(vols[:-2]) / max(len(vols)-2, 1)
    
    # Check last 2 candles for extreme moves
    last_v = float(k5[-2]["v"])
    last_o = float(k5[-2]["o"]); last_c = float(k5[-2]["c"])
    last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
    
    curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
    curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
    
    # === PUMP -> SHORT ===
    # Single candle pump: vol > 5x avg, price > 2%, then reversal candle
    if last_v > avg_v * 5 and last_chg > 2.0 and curr_chg < -0.3:
        score = min(int(last_v/avg_v * 8), 80)
        reasons = ["PUMP_REV(x%.0f +%.1f%%)" % (last_v/avg_v, last_chg)]
        
        # CVD check: if CVD was buying during pump, it's exhausted
        cv5 = calc_cvd(k5, 3)
        if cv5 < -10:
            score += 10; reasons.append("CVD_exhaust")
        
        return ("pump_short", "short", score, reasons)
    
    # Multi-candle cumulative pump
    if len(k5) >= 5:
        cum_chg_3 = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-4,-1) if float(k5[i]["o"])>0)
        v3 = sum(float(k5[i]["v"]) for i in range(-4,-1))
        v3_prev = sum(float(k5[i]["v"]) for i in range(-7,-4))
        v3_ratio = v3 / max(v3_prev, 0.001)
        
        if cum_chg_3 > 3.0 and v3_ratio > 4 and curr_chg < 0:
            score = min(int(v3_ratio * 10), 80)
            reasons = ["CUMUL_PUMP(3c+%.1f%%_x%.0f)" % (cum_chg_3, v3_ratio)]
            
            cv5 = calc_cvd(k5, 3)
            if cv5 < -10:
                score += 10; reasons.append("CVD_exhaust")
            
            return ("pump_short", "short", score, reasons)
    
    # === DUMP -> LONG ===
    if last_v > avg_v * 5 and last_chg < -2.0 and curr_chg > 0.3:
        score = min(int(last_v/avg_v * 8), 80)
        reasons = ["DUMP_REV(x%.0f %.1f%%)" % (last_v/avg_v, abs(last_chg))]
        cv5 = calc_cvd(k5, 3)
        if cv5 > 10:
            score += 10; reasons.append("CVD_exhaust")
        return ("dump_long", "long", score, reasons)
    
    if len(k5) >= 5:
        cum_chg_3 = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-4,-1) if float(k5[i]["o"])>0)
        v3 = sum(float(k5[i]["v"]) for i in range(-4,-1))
        v3_prev = sum(float(k5[i]["v"]) for i in range(-7,-4))
        v3_ratio = v3 / max(v3_prev, 0.001)
        
        if cum_chg_3 < -3.0 and v3_ratio > 4 and curr_chg > 0:
            score = min(int(v3_ratio * 10), 80)
            reasons = ["CUMUL_DUMP(3c%.1f%%_x%.0f)" % (abs(cum_chg_3), v3_ratio)]
            cv5 = calc_cvd(k5, 3)
            if cv5 > 10:
                score += 10; reasons.append("CVD_exhaust")
            return ("dump_long", "long", score, reasons)
    
    return None

while True:
    try:
        t0 = time.time()
        now_ts = time.time()
        signals = []
        
        def scan_coin(sym):
            try:
                k5 = fetch_klines(sym, "5m", 40)
                if not k5: return None
                result = detect_reversal(k5)
                if not result: return None
                ptype, direction, score, reasons = result
                
                # Cooldown
                if sym in _cooldown and now_ts - _cooldown[sym] < 600:
                    return None
                
                price = fetch_price(sym)
                if not price: return None
                
                # OB confirmation
                try:
                    ob = fetch_orderbook_imbalance(sym, 100)
                    if ob:
                        imb = ob.get("imbalance", 0)
                        if direction == "short" and imb < -20:
                            score += 15; reasons.append("OB_ask:" + str(int(imb)) + "%")
                        elif direction == "long" and imb > 20:
                            score += 15; reasons.append("OB_bid:" + str(int(imb)) + "%")
                        elif direction == "short" and imb > 10:
                            score -= 10  # OB opposes
                        elif direction == "long" and imb < -10:
                            score -= 10
                except: pass
                
                return (sym, direction, score, reasons, price)
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(scan_coin, s): s for s in COINS}
            for f in as_completed(futures, timeout=30):
                r = f.result()
                if r and r[2] >= 30:  # score >= 30
                    signals.append(r)
        
        if signals:
            signals.sort(key=lambda x: -x[2])
            signals = signals[:4]  # max 4
            
            for sym, direction, score, reasons, price in signals:
                _cooldown[sym] = now_ts
            
            t = datetime.now(BJT).strftime("%m/%d %H:%M")
            lines = ["----------------", "  \U0001f504 Reversal V1 | %s" % t, "----------------"]
            
            longs = [s for s in signals if s[1] == "long"]
            shorts = [s for s in signals if s[1] == "short"]
            
            if longs:
                lines.append("  \U0001f7e2 DUMP->LONG (buy the dip)")
                for sym, direction, score, reasons, price in longs:
                    sym_s = sym.replace("USDT","")
                    conf = "\U0001f525" if score >= 50 else "\U0001f4ca"
                    lines.append("    %s %s %dpt $%s" % (conf, sym_s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:3]))
            
            if shorts:
                lines.append("  \U0001f534 PUMP->SHORT (fade the pump)")
                for sym, direction, score, reasons, price in shorts:
                    sym_s = sym.replace("USDT","")
                    conf = "\U0001f525" if score >= 50 else "\U0001f4ca"
                    lines.append("    %s %s %dpt $%s" % (conf, sym_s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:3]))
            
            lines.append("----------------")
            
            tracker_sigs = [{"sym": s[0].replace("USDT",""), "dir": s[1], "price": s[4], "score": s[2], "reasons": s[3]} for s in signals]
            track_signals(tracker_sigs, source="reversal")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
            print("[Reversal] %d signals (L:%d S:%d)" % (len(signals), len(longs), len(shorts)))
        
        elapsed = time.time() - t0
        time.sleep(max(5, 40 - elapsed))
    except Exception as e:
        print("[Reversal] error:", e)
        import traceback; traceback.print_exc()
        time.sleep(30)
