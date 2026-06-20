#!/usr/bin/env python3
"""demon_hunter.py v2 - Always-on microcap mean-reversion + mercu bonus
v2 changes: fixed coin list (not mercu-gated), 1m+5m dual detection,
VWAP overextension, faster cooldown"""

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

# Fixed scan list - always scan these regardless of mercu
COINS = [
    "IOUSDT","ENAUSDT","TAOUSDT","ONDOUSDT","ALLOUSDT","TRUMPUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT",
    "COAIUSDT","MEGAUSDT","CHIPUSDT","ESPORTSUSDT","SENTUSDT",
    "JASMYUSDT","ALGOUSDT","FETUSDT","WLDUSDT","HYPEUSDT",
    "INJUSDT","APTUSDT","DASHUSDT","ZECUSDT","AAVEUSDT","JCTUSDT"
]

_cooldown = {}

def load(name, ttl=180):
    p = os.path.join(DATA, name)
    if not os.path.exists(p): return None
    if time.time() - os.path.getmtime(p) > ttl: return None
    with open(p) as f: return json.load(f)

def get_mercu_bonus(sym_clean, direction):
    """Get bonus points from mercu data. Returns (bonus, label)"""
    bonus = 0
    labels = []
    
    # State anomalies
    anom = load("anomaly-v4.json", ttl=120)
    if anom:
        for s in anom.get("state_anomalies", []):
            if str(s.get("symbol", "")).upper() == sym_clean:
                scenario = s.get("scenario", "")
                if direction == "short" and scenario in ("DISTRIB", "BEAR"):
                    bonus += 15; labels.append("MER:" + scenario)
                elif direction == "long" and scenario in ("ACCUM", "BULL"):
                    bonus += 15; labels.append("MER:" + scenario)
                elif direction == "short" and scenario == "BULL":
                    bonus -= 10
                elif direction == "long" and scenario == "DISTRIB":
                    bonus -= 10
    
    # Rank check
    rank = load("rank.json", ttl=300)
    if rank:
        for item in rank.get("top", [])[:5]:
            if str(item.get("sym", "")).replace("$", "").upper() == sym_clean:
                bonus += 5; labels.append("Rank#%d" % item.get("rank", 0))
                break
    
    # Surge check
    surge = load("surge.json", ttl=120)
    if surge:
        for item in surge.get("items", []):
            if str(item.get("sym", "")).upper() == sym_clean:
                accel = float(item.get("accel", 0))
                if accel >= 1.5:
                    bonus += 8; labels.append("Surge:x%.1f" % accel)
                break
    
    return bonus, labels

def calc_vwap(k5):
    """Calculate VWAP from kline data"""
    if not k5: return 0
    total_pv = 0; total_v = 0
    for k in k5[-24:]:  # Last 2 hours
        v = float(k["v"])
        typical = (float(k["h"]) + float(k["l"]) + float(k["c"])) / 3
        total_pv += typical * v
        total_v += v
    return total_pv / total_v if total_v > 0 else 0

def detect(k5, k1=None):
    """Multi-timeframe mean-reversion detection"""
    if not k5 or len(k5) < 12:
        return None
    
    vols = [float(k["v"]) for k in k5]
    avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
    if avg_v < 1: return None
    
    # Current price
    price = float(k5[-1]["c"])
    vwap = calc_vwap(k5)
    
    # VWAP deviation (overextension)
    vwap_dev = (price - vwap) / vwap * 100 if vwap > 0 else 0
    
    # Last 2 candles
    p_o = float(k5[-2]["o"]); p_c = float(k5[-2]["c"]); p_v = float(k5[-2]["v"])
    p_chg = (p_c - p_o) / p_o * 100 if p_o > 0 else 0
    c_o = float(k5[-1]["o"]); c_c = float(k5[-1]["c"])
    c_chg = (c_c - c_o) / c_o * 100 if c_o > 0 else 0
    vr = p_v / max(avg_v, 0.001)
    
    # === SHORT signals ===
    short_score = 0; short_reasons = []
    
    # Pattern 1: Single candle pump reversal
    if vr >= 2.0 and p_chg >= 2.0 and c_chg <= 0.2:
        short_score = min(int(vr * 7 + p_chg * 3), 70)
        short_reasons = ["PUMP(%.0fx +%.1f%%)" % (vr, p_chg)]
    
    # Pattern 2: Cumulative pump
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100
                   for i in range(-5, -2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5, -2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8, -5))
        v3r = v3 / max(v3p, 0.001)
        if cum3 >= 3.0 and v3r >= 1.8 and c_chg <= 0.3:
            s = min(int(v3r * 5 + cum3 * 3), 65)
            if s > short_score:
                short_score = s
                short_reasons = ["CUMUL_PUMP(3c +%.1f%% x%.0f)" % (cum3, v3r)]
    
    # Pattern 3: VWAP overextension (>5% above VWAP = mean-revert)
    if vwap_dev > 5.0 and c_chg <= 0.3:
        s = min(int(vwap_dev * 5), 60)
        if s > short_score:
            short_score = s
            short_reasons = ["VWAP_hi(+%.1f%%)" % vwap_dev]
    
    if short_score > 0:
        # CVD confirmation
        cv5 = calc_cvd(k5, 3)
        if cv5 < -5: short_score += 8; short_reasons.append("CVD_exhaust")
        
        # 1m confirmation
        if k1:
            k1_chg = (float(k1[-1]["c"]) - float(k1[-1]["o"])) / float(k1[-1]["o"]) * 100 if float(k1[-1]["o"]) > 0 else 0
            if k1_chg < -0.1: short_score += 5
    
    # === LONG signals ===
    long_score = 0; long_reasons = []
    
    if vr >= 2.0 and p_chg <= -2.0 and c_chg >= -0.2:
        long_score = min(int(vr * 7 + abs(p_chg) * 3), 70)
        long_reasons = ["DUMP(%.0fx %.1f%%)" % (vr, abs(p_chg))]
    
    if len(k5) >= 8:
        cum3 = sum((float(k5[i]["c"]) - float(k5[i]["o"])) / float(k5[i]["o"]) * 100
                   for i in range(-5, -2) if float(k5[i]["o"]) > 0)
        v3 = sum(float(k5[i]["v"]) for i in range(-5, -2))
        v3p = sum(float(k5[i]["v"]) for i in range(-8, -5))
        v3r = v3 / max(v3p, 0.001)
        if cum3 <= -3.0 and v3r >= 1.8 and c_chg >= -0.3:
            s = min(int(v3r * 5 + abs(cum3) * 3), 65)
            if s > long_score:
                long_score = s
                long_reasons = ["CUMUL_DUMP(3c %.1f%% x%.0f)" % (abs(cum3), v3r)]
    
    if vwap_dev < -5.0 and c_chg >= -0.3:
        s = min(int(abs(vwap_dev) * 5), 60)
        if s > long_score:
            long_score = s
            long_reasons = ["VWAP_lo(%.1f%%)" % abs(vwap_dev)]
    
    if long_score > 0:
        cv5 = calc_cvd(k5, 3)
        if cv5 > 5: long_score += 8; long_reasons.append("CVD_exhaust")
        
        if k1:
            k1_chg = (float(k1[-1]["c"]) - float(k1[-1]["o"])) / float(k1[-1]["o"]) * 100 if float(k1[-1]["o"]) > 0 else 0
            if k1_chg > 0.1: long_score += 5
    
    # Pick best
    if short_score >= 20 and short_score >= long_score:
        return ("short", short_score, short_reasons, price)
    elif long_score >= 20 and long_score > short_score:
        return ("long", long_score, long_reasons, price)
    return None

print("[Demon v2] Always-on microcap hunter starting...")
feishu_app_send("Demon v2 | 27coins +1m+VWAP | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT)

while True:
    try:
        t0 = time.time()
        now_ts = time.time()
        signals = []
        
        def scan(sym):
            try:
                k5 = fetch_klines(sym, "5m", 30)
                k1 = fetch_klines(sym, "1m", 15)
                if not k5: return None
                
                result = detect(k5, k1)
                if not result: return None
                direction, score, reasons, price = result
                
                if sym in _cooldown and now_ts - _cooldown[sym] < 180:
                    return None
                
                # Mercu bonus
                sym_c = sym.replace("USDT", "")
                bonus, blabels = get_mercu_bonus(sym_c, direction)
                score += bonus
                reasons.extend(blabels)
                
                # OB confirmation
                try:
                    ob = fetch_orderbook_imbalance(sym, 100)
                    if ob:
                        imb = ob.get("imbalance", 0)
                        if direction == "short" and imb < -15:
                            score += 8; reasons.append("OB_ask:" + str(int(imb)) + "%")
                        elif direction == "long" and imb > 15:
                            score += 8; reasons.append("OB_bid:" + str(int(imb)) + "%")
                        elif direction == "short" and imb > 25:
                            score -= 15
                        elif direction == "long" and imb < -25:
                            score -= 15
                except: pass
                
                return (sym, direction, score, reasons, price)
            except:
                return None
        
        ex = ThreadPoolExecutor(max_workers=10)
        try:
            futures = {ex.submit(scan, c): c for c in COINS}
            done, not_done = wait(futures, timeout=22)
            for f in done:
                try:
                    r = f.result(timeout=0)
                    if r and r[2] >= 20:
                        signals.append(r)
                except: pass
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
            lines = ["----------------", "  Demon V2 | %s" % t, "----------------"]
            
            longs = [s for s in signals if s[1] == "long"]
            shorts = [s for s in signals if s[1] == "short"]
            
            if shorts:
                lines.append("  FADE PUMP -> SHORT")
                for sym, direction, score, reasons, price in shorts:
                    s = sym.replace("USDT", "")
                    conf = "HOT" if score >= 50 else ""
                    lines.append("    %s %s %dpt $%s" % (conf, s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:4]))
            
            if longs:
                lines.append("  BUY DUMP -> LONG")
                for sym, direction, score, reasons, price in longs:
                    s = sym.replace("USDT", "")
                    conf = "HOT" if score >= 50 else ""
                    lines.append("    %s %s %dpt $%s" % (conf, s, score, str(price)))
                    lines.append("      " + " | ".join(reasons[:4]))
            
            lines.append("----------------")
            
            tracker_sigs = [{"sym": s[0].replace("USDT",""), "dir": s[1], "price": s[4], "score": s[2], "reasons": s[3]} for s in signals]
            track_signals(tracker_sigs, source="demon")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT)
            print("[Demon v2] %d signals (S:%d L:%d)" % (len(signals), len(shorts), len(longs)))
        else:
            print("[Demon v2] 0 signals")
        
        elapsed = time.time() - t0
        time.sleep(max(5, 30 - elapsed))
    except Exception as e:
        print("[Demon v2] error:", e)
        import traceback; traceback.print_exc()
        time.sleep(30)