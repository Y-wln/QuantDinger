#!/usr/bin/env python3
"""demon_hunter.py v1 - Mercu state-anomaly + mean-reversion for microcaps
Core thesis: microcaps mean-revert. Pump->short, dump->long.
Pre-filtered by mercu.win AI state anomalies (ACCUM/BULL/DISTRIB/BEAR)."""

import sys, os, json, time
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import (fetch_klines, fetch_price, fetch_orderbook_imbalance,
                         feishu_app_send, calc_cvd)
from signal_tracker import track_signals
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, wait

BJT = timezone(timedelta(hours=8))
CHAT = "oc_58c90b36ddb0d64439c64ed83a16b47b"
DATA = "/home/ubuntu/scripts/agents/mercu_data"

_cooldown = {}
_seen_states = {}

def load(name, ttl=180):
    p = os.path.join(DATA, name)
    if not os.path.exists(p): return None
    if time.time() - os.path.getmtime(p) > ttl: return None
    with open(p) as f: return json.load(f)

def get_hotlist():
    """Get coins with active mercu state anomalies + top rank + surge"""
    hot = set()
    reasons = {}
    
    # State anomalies (highest weight)
    anom = load("anomaly-v4.json", ttl=120)
    if anom:
        for s in anom.get("state_anomalies", []):
            sym = str(s.get("symbol", "")).upper()
            scenario = s.get("scenario", "")
            label = s.get("scenario_label", "")
            hot.add(sym)
            reasons[sym] = "state:" + scenario
    
    # Rank top 10
    rank = load("rank.json", ttl=300)
    if rank:
        for item in rank.get("top", [])[:10]:
            sym = str(item.get("sym", "")).replace("$", "").upper()
            hot.add(sym)
            if sym not in reasons:
                reasons[sym] = "rank:" + str(item.get("rank", ""))
    
    # Surge
    surge = load("surge.json", ttl=120)
    if surge:
        for item in surge.get("items", []):
            sym = str(item.get("sym", "")).upper()
            if float(item.get("accel", 0)) >= 1.5:
                hot.add(sym)
                if sym not in reasons:
                    reasons[sym] = "surge:x%.1f" % float(item.get("accel", 0))
    
    return hot, reasons

def detect_mean_reversion(k5):
    """Tuned for microcap mean-reversion"""
    if not k5 or len(k5) < 12:
        return None
    
    vols = [float(k["v"]) for k in k5]
    avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
    if avg_v < 1:
        return None
    
    # Last 2 candles
    prev_o = float(k5[-2]["o"]); prev_c = float(k5[-2]["c"])
    prev_v = float(k5[-2]["v"])
    prev_chg = (prev_c - prev_o) / prev_o * 100 if prev_o > 0 else 0
    
    curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
    curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
    
    vr = prev_v / max(avg_v, 0.001)
    
    # === PUMP -> SHORT (fade the pump) ===
    # Single fat candle pump + reversal
    if vr >= 2.0 and prev_chg >= 2.0 and curr_chg <= 0.1:
        score = min(int(vr * 8 + abs(prev_chg) * 3), 80)
        reasons = ["PUMP_REV(%.0fx +%.1f%%)" % (vr, prev_chg)]
        
        cv5 = calc_cvd(k5, 3)
        if cv5 < -5:
            score += 10
            reasons.append("CVD_exhaust")
        
        return ("short", score, reasons)
    
    # Cumulative pump over 3 candles
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100 
                   for i in range(-5, -2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5, -2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8, -5))
        v3r = v3 / max(v3p, 0.001)
        
        if cum3 >= 3.0 and v3r >= 2.0 and curr_chg <= 0.2:
            score = min(int(v3r * 6 + cum3 * 3), 80)
            reasons = ["CUMUL_PUMP(3c +%.1f%% x%.0f)" % (cum3, v3r)]
            
            cv5 = calc_cvd(k5, 3)
            if cv5 < -5:
                score += 10
                reasons.append("CVD_exhaust")
            
            return ("short", score, reasons)
    
    # === DUMP -> LONG (buy the dip) ===
    if vr >= 2.0 and prev_chg <= -2.0 and curr_chg >= -0.1:
        score = min(int(vr * 8 + abs(prev_chg) * 3), 80)
        reasons = ["DUMP_REV(%.0fx %.1f%%)" % (vr, abs(prev_chg))]
        
        cv5 = calc_cvd(k5, 3)
        if cv5 > 5:
            score += 10
            reasons.append("CVD_exhaust")
        
        return ("long", score, reasons)
    
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100 
                   for i in range(-5, -2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5, -2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8, -5))
        v3r = v3 / max(v3p, 0.001)
        
        if cum3 <= -3.0 and v3r >= 2.0 and curr_chg >= -0.2:
            score = min(int(v3r * 6 + abs(cum3) * 3), 80)
            reasons = ["CUMUL_DUMP(3c %.1f%% x%.0f)" % (abs(cum3), v3r)]
            
            cv5 = calc_cvd(k5, 3)
            if cv5 > 5:
                score += 10
                reasons.append("CVD_exhaust")
            
            return ("long", score, reasons)
    
    return None

print("[Demon v1] Microcap mean-reversion hunter starting...")
feishu_app_send("Demon Hunter v1 | Mercu-state + Mean-reversion | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT)

while True:
    try:
        t0 = time.time()
        now_ts = time.time()
        
        hotlist, hot_reasons = get_hotlist()
        
        if not hotlist:
            time.sleep(30)
            continue
        
        # Convert to USDT pairs
        coins = [c + "USDT" for c in hotlist if len(c) <= 8]
        if not coins:
            time.sleep(30)
            continue
        
        signals = []
        
        def scan(sym):
            try:
                k5 = fetch_klines(sym, "5m", 40)
                if not k5:
                    return None
                
                result = detect_mean_reversion(k5)
                if not result:
                    return None
                
                direction, score, reasons = result
                
                # Cooldown: 5 min per coin
                if sym in _cooldown and now_ts - _cooldown[sym] < 300:
                    return None
                
                price = fetch_price(sym)
                if not price:
                    return None
                
                # Mercu state bonus
                sym_clean = sym.replace("USDT", "")
                if sym_clean in hot_reasons:
                    state = hot_reasons[sym_clean]
                    if direction == "short" and ("DISTRIB" in state or "BEAR" in state):
                        score += 15
                        reasons.append("MER:" + state)
                    elif direction == "long" and ("ACCUM" in state or "BULL" in state):
                        score += 15
                        reasons.append("MER:" + state)
                    elif direction == "short" and ("BULL" in state):
                        score -= 10  # Contradiction
                    elif direction == "long" and ("DISTRIB" in state):
                        score -= 10
                
                # OB confirmation
                try:
                    ob = fetch_orderbook_imbalance(sym, 100)
                    if ob:
                        imb = ob.get("imbalance", 0)
                        if direction == "short" and imb < -15:
                            score += 10
                            reasons.append("OB_ask:" + str(int(imb)) + "%")
                        elif direction == "long" and imb > 15:
                            score += 10
                            reasons.append("OB_bid:" + str(int(imb)) + "%")
                        elif direction == "short" and imb > 20:
                            score -= 15  # Strong bid wall, don't short
                        elif direction == "long" and imb < -20:
                            score -= 15
                except:
                    pass
                
                return (sym, direction, score, reasons, price)
            except:
                return None
        
        ex = ThreadPoolExecutor(max_workers=8)
        try:
            futures = {ex.submit(scan, c): c for c in coins}
            done, not_done = wait(futures, timeout=20)
            for f in done:
                try:
                    r = f.result(timeout=0)
                    if r and r[2] >= 25:
                        signals.append(r)
                except:
                    pass
            for f in not_done:
                f.cancel()
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
        
        if signals:
            signals.sort(key=lambda x: -x[2])
            signals = signals[:4]
            
            for sym, direction, score, reasons, price in signals:
                _cooldown[sym] = now_ts
            
            t = datetime.now(BJT).strftime("%m/%d %H:%M")
            lines = ["----------------", "  Demon V1 | %s" % t, "----------------"]
            
            longs = [s for s in signals if s[1] == "long"]
            shorts = [s for s in signals if s[1] == "short"]
            
            if shorts:
                lines.append("  FADE PUMP -> SHORT")
                for sym, direction, score, reasons, price in shorts:
                    s = sym.replace("USDT", "")
                    conf = "HOT" if score >= 50 else "OK"
                    lines.append("    %s %s %dpt $%s" % (conf, s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:3]))
            
            if longs:
                lines.append("  BUY DUMP -> LONG")
                for sym, direction, score, reasons, price in longs:
                    s = sym.replace("USDT", "")
                    conf = "HOT" if score >= 50 else "OK"
                    lines.append("    %s %s %dpt $%s" % (conf, s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:3]))
            
            lines.append("----------------")
            
            tracker_sigs = [{"sym": s[0].replace("USDT",""), "dir": s[1], "price": s[4], "score": s[2], "reasons": s[3]} for s in signals]
            track_signals(tracker_sigs, source="demon")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT)
            print("[Demon] %d signals (S:%d L:%d) from %d hot coins" % (len(signals), len(shorts), len(longs), len(coins)))
        else:
            print("[Demon] 0 signals from %d hot coins" % len(coins))
        
        elapsed = time.time() - t0
        time.sleep(max(5, 35 - elapsed))
        
    except Exception as e:
        print("[Demon] error:", e)
        import traceback; traceback.print_exc()
        time.sleep(30)