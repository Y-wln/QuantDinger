import sys, os, time, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from signal_tracker import track_signals
from hermes_core import fetch_orderbook_imbalance, feishu_app_send, fetch_price, fetch_klines, calc_cvd
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BJT = timezone(timedelta(hours=8))
CHAT_ID = "oc_58c90b36ddb0d64439c64ed83a16b47b"

COINS = ["CHZUSDT","IOUSDT","SENTUSDT","ENAUSDT","UNIUSDT",
    "TAOUSDT","ONDOUSDT","PUMPUSDT","ALLOUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT",
    "MEGAUSDT","CHIPUSDT","KAITOUSDT","ESPORTSUSDT"]

_pending = {}; _alerted = {}; _last_score = {}

# Trend: check 4h kline for trend direction (simple EMA)
_trend_map = {}

def check_trend(sym):
    if sym in _trend_map: return _trend_map[sym]
    try:
        k4 = fetch_klines(sym, "4h", 8)
        if k4 and len(k4) >= 6:
            closes = [float(k["c"]) for k in k4]
            chg = (closes[-1] - closes[-6]) / closes[-6] * 100
            _trend_map[sym] = chg
            return chg
    except: pass
    _trend_map[sym] = -5  # default downtrend
    return -5

def allow_long(sym):
    chg = check_trend(sym)
    return chg > 1.0 or chg < -20.0

print("[Ambush v5 TREND] OB + 4h-trend-filter | " + datetime.now(BJT).strftime("%H:%M"))
feishu_app_send("Ambush v5 | +trend-filter | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

while True:
    try:
        t0 = time.time(); now_ts = time.time()
        _trend_map = {}  # Refresh trend each cycle
        signals = []
        
        def scan_coin(sym):
            try:
                ob = fetch_orderbook_imbalance(sym, 100)
                if not ob: return None
                imb = ob.get("imbalance", 0)
                if abs(imb) < 40: return None
                price = fetch_price(sym)
                if not price: return None
                return (sym, imb, price)
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(scan_coin, s): s for s in COINS}
            for f in as_completed(futures, timeout=35):
                r = f.result()
                if not r: continue
                sym, imb, price = r
                direction = "long" if imb > 0 else "short"
                pkey = sym + "_" + direction
                
                if pkey in _pending:
                    prev_ts, prev_imb, prev_price = _pending[pkey]
                    if now_ts - prev_ts < 60:
                        avg_imb = (abs(imb) + abs(prev_imb)) // 2
                        cv5 = 0
                        try:
                            k5 = fetch_klines(sym, "5m", 30)
                            if k5: cv5 = calc_cvd(k5, 3)
                        except: pass
                        
                        score = avg_imb
                        if (direction == "long" and cv5 > 10) or (direction == "short" and cv5 < -10):
                            score += 10
                        elif (direction == "long" and cv5 < 0) or (direction == "short" and cv5 > 0):
                            score -= 15
                        
                        prev_score = _last_score.get(pkey, 0)
                        if score > prev_score: score += 5
                        _last_score[pkey] = score
                        
                        if score >= 45:
                            if direction == "long" and not allow_long(sym):
                                pass  # blocked by trend filter
                            else:
                                signals.append((sym, direction, avg_imb, price, score, cv5))
                            _alerted[pkey] = now_ts
                        del _pending[pkey]
                    else:
                        _pending[pkey] = (now_ts, imb, price)
                else:
                    _pending[pkey] = (now_ts, imb, price)
        
        for key in list(_pending.keys()):
            if now_ts - _pending[key][0] > 90:
                del _pending[key]
        
        if signals:
            signals.sort(key=lambda x: -x[4])
            signals = signals[:3]
            t_str = datetime.now(BJT).strftime("%m/%d %H:%M")
            lines = ["----------------", "  Ambush V5 | %s" % t_str, "----------------"]
            
            longs = [s for s in signals if s[1] == "long"]
            shorts = [s for s in signals if s[1] == "short"]
            
            if longs:
                lines.append("  LONG (trend-OK)")
                for sym, direction, imb, price, score, cv5 in longs[:3]:
                    s = sym.replace("USDT","")
                    lines.append("    %s %dpt $%s" % (s, score, str(price)))
            
            if shorts:
                lines.append("  SHORT")
                for sym, direction, imb, price, score, cv5 in shorts[:3]:
                    s = sym.replace("USDT","")
                    lines.append("    %s %dpt $%s" % (s, score, str(price)))
            
            lines.append("----------------")
            ambush_sigs = [{"sym": s[0].replace("USDT",""), "dir": s[1], "price": s[3], "score": s[4], "reasons": ["OB:"+str(s[2])+"%", "CVD:"+str(s[5])]} for s in signals]
            track_signals(ambush_sigs, source="ambush")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
            print("[AmbushV5] %d signals (L:%d S:%d)" % (len(signals), len(longs), len(shorts)))
        
        elapsed = time.time() - t0
        time.sleep(max(3, 15 - elapsed))
    except Exception as e:
        print("[AmbushV5] error:", e)
        import traceback; traceback.print_exc()
        time.sleep(15)