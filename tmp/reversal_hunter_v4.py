# reversal_hunter.py v2 - mean-reversion strategy (fixed hang)
# Extreme pump -> short, extreme dump -> long
# The opposite of trend-following

import sys, os, time, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import (fetch_klines, fetch_price, fetch_orderbook_imbalance,
                         feishu_app_send, calc_cvd)
from signal_tracker import track_signals
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

BJT = timezone(timedelta(hours=8))
CHAT_ID = "oc_58c90b36ddb0d64439c64ed83a16b47b"

COINS = ["CHZUSDT","IOUSDT","SENTUSDT","ENAUSDT","UNIUSDT",
    "TAOUSDT","ONDOUSDT","ALLOUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT",
    "MEGAUSDT","CHIPUSDT","KAITOUSDT","ESPORTSUSDT","MITOUSDT","SIRENUSDT",
    "JASMYUSDT","ALGOUSDT","JCTUSDT","DOGEUSDT","LTCUSDT"]

_cooldown = {}

print("[Reversal v2] Mean-reversion hunter starting (fixed hang)...")
feishu_app_send("Reversal Hunter v2 | fixed hang + relaxed | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

def detect_reversal(k5):
    """Detect extreme moves ripe for reversal.
    Returns (signal_type, direction, score, reasons) or None.
    """
    if not k5 or len(k5) < 15: return None
    
    vols = [float(k["v"]) for k in k5[-15:]]
    avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
    
    last_v = float(k5[-2]["v"])
    last_o = float(k5[-2]["o"]); last_c = float(k5[-2]["c"])
    last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
    
    curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
    curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
    
    # === PUMP -> SHORT ===
    # Single candle pump: vol > 3x avg, price > 1.5%, then reversal candle
    if last_v > avg_v * 2 and last_chg > 1.0 and curr_chg < -0.1:
        score = min(int(last_v/avg_v * 6), 70)
        reasons = ["PUMP_REV(x%.0f +%.1f%%)" % (last_v/avg_v, last_chg)]
        cv5 = calc_cvd(k5, 3)
        if cv5 < -10:
            score += 10; reasons.append("CVD_exhaust")
        return ("pump_short", "short", score, reasons)
    
    # Multi-candle cumulative pump (2% over 3c, vol>3x)
    if len(k5) >= 6:
        cum_chg_3 = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-5,-2) if float(k5[i]["o"])>0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3_prev = sum(float(k5[i]["v"]) for i in range(-8,-5))
        v3_ratio = v3 / max(v3_prev, 0.001)
        
        if cum_chg_3 > 1.5 and v3_ratio > 2 and curr_chg < 0:
            score = min(int(v3_ratio * 8), 70)
            reasons = ["CUMUL_PUMP(3c+%.1f%%_x%.0f)" % (cum_chg_3, v3_ratio)]
            cv5 = calc_cvd(k5, 3)
            if cv5 < -10:
                score += 10; reasons.append("CVD_exhaust")
            return ("pump_short", "short", score, reasons)
    
    # === DUMP -> LONG ===
    if last_v > avg_v * 2 and last_chg < -1.0 and curr_chg > 0.1:
        score = min(int(last_v/avg_v * 6), 70)
        reasons = ["DUMP_REV(x%.0f %.1f%%)" % (last_v/avg_v, abs(last_chg))]
        cv5 = calc_cvd(k5, 3)
        if cv5 > 10:
            score += 10; reasons.append("CVD_exhaust")
        return ("dump_long", "long", score, reasons)
    
    if len(k5) >= 6:
        cum_chg_3 = sum((float(k5[i]["c"])-float(k5[i]["o"]))/float(k5[i]["o"])*100 for i in range(-5,-2) if float(k5[i]["o"])>0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5,-2))
        v3_prev = sum(float(k5[i]["v"]) for i in range(-8,-5))
        v3_ratio = v3 / max(v3_prev, 0.001)
        
        if cum_chg_3 < -1.5 and v3_ratio > 2 and curr_chg > 0:
            score = min(int(v3_ratio * 8), 70)
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
                
                if sym in _cooldown and now_ts - _cooldown[sym] < 300:
                    return None
                
                price = fetch_price(sym)
                if not price: return None
                
                try:
                    ob = fetch_orderbook_imbalance(sym, 100)
                    if ob:
                        imb = ob.get("imbalance", 0)
                        if direction == "short" and imb < -20:
                            score += 15; reasons.append("OB_ask:" + str(int(imb)) + "%")
                        elif direction == "long" and imb > 20:
                            score += 15; reasons.append("OB_bid:" + str(int(imb)) + "%")
                        elif direction == "short" and imb > 10:
                            score -= 10
                        elif direction == "long" and imb < -10:
                            score -= 10
                except: pass
                
                return (sym, direction, score, reasons, price)
            except:
                return None
        
        # FIX: Use wait() with timeout + cancel_futures to prevent hanging
        ex = ThreadPoolExecutor(max_workers=10)
        try:
            futures = {ex.submit(scan_coin, s): s for s in COINS}
            done, not_done = wait(futures, timeout=20)
            for f in done:
                try:
                    r = f.result(timeout=0)
                    if r and r[2] >= 15:
                        signals.append(r)
                except: pass
            for f in not_done:
                f.cancel()
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
        
        longs = [s for s in signals if s[1] == "long"]
        shorts = [s for s in signals if s[1] == "short"]
        
        if signals:
            signals.sort(key=lambda x: -x[2])
            signals = signals[:5]
            
            for sym, direction, score, reasons, price in signals:
                _cooldown[sym] = now_ts
            
            t = datetime.now(BJT).strftime("%m/%d %H:%M:%S")
            lines = ["----------------", "  \U0001f504 Reversal V2 | %s" % t, "----------------"]
            
            if longs:
                lines.append("  \U0001f7e2 DUMP->LONG (buy the dip)")
                for sym, direction, score, reasons, price in longs:
                    sym_s = sym.replace("USDT","")
                    conf = "\U0001f525" if score >= 45 else "\U0001f4ca"
                    lines.append("    %s %s %dpt $%s" % (conf, sym_s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:3]))
            
            if shorts:
                lines.append("  \U0001f534 PUMP->SHORT (fade the pump)")
                for sym, direction, score, reasons, price in shorts:
                    sym_s = sym.replace("USDT","")
                    conf = "\U0001f525" if score >= 45 else "\U0001f4ca"
                    lines.append("    %s %s %dpt $%s" % (conf, sym_s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:3]))
            
            lines.append("----------------")
            
            tracker_sigs = [{"sym": s[0].replace("USDT",""), "dir": s[1], "price": s[4], "score": s[2], "reasons": s[3]} for s in signals]
            track_signals(tracker_sigs, source="reversal")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
        
        elapsed = time.time() - t0
        print("[RevV2] cycle %.1fs | %d signals (L:%d S:%d)" % (elapsed, len(signals), len(longs), len(shorts)))
        time.sleep(max(2, 25 - elapsed))
    except Exception as e:
        print("[RevV2] error:", e)
        import traceback; traceback.print_exc()
        time.sleep(30)