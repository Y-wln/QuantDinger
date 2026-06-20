import sys, os, time, json, urllib.request
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from signal_tracker import track_signals
from hermes_core import fetch_orderbook_imbalance, feishu_app_send, fetch_price, fetch_klines, calc_cvd
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BJT = timezone(timedelta(hours=8))
CHAT_ID = "oc_58c90b36ddb0d64439c64ed83a16b47b"
PROXY = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})

COINS = ["CHZUSDT","IOUSDT","SENTUSDT","ENAUSDT","UNIUSDT",
    "TAOUSDT","ONDOUSDT","PUMPUSDT","ALLOUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT",
    "MEGAUSDT","CHIPUSDT","KAITOUSDT","ESPORTSUSDT"]

_pending = {}; _alerted = {}; _last_score = {}
_trend_cache = {}  # sym -> 24h change%

def get_trends():
    """Fetch all 24h changes once per cycle"""
    try:
        opener = urllib.request.build_opener(PROXY)
        resp = opener.open("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=10)
        data = json.loads(resp.read())
        for t in data:
            _trend_cache[t["symbol"]] = float(t.get("priceChangePercent", 0))
        return True
    except:
        return False

def allow_long(sym):
    """Trend filter: only long if uptrend or capitulation"""
    chg = _trend_cache.get(sym, -5)  # default: assume downtrend
    return chg > 1.0 or chg < -20.0

print("[Ambush v5 TREND] OB + trend-filter | " + datetime.now(BJT).strftime("%H:%M"))
feishu_app_send("Ambush v5 | +trend-filter(longs only) | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

while True:
    try:
        t0 = time.time(); now_ts = time.time()
        get_trends()  # Refresh trend data
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
        
        ex = ThreadPoolExecutor(max_workers=8)
        try:
            futures = {ex.submit(scan_coin, s): s for s in COINS}
            done, not_done = wait(futures, timeout=35)
            for f in done:
                r = f.result(timeout=0)
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
                            # TREND FILTER for longs
                            if direction == "long" and not allow_long(sym):
                                pass  # Skip: coin in slow bleed
                            else:
                                signals.append((sym, direction, avg_imb, price, score, cv5))
                            _alerted[pkey] = now_ts
                        del _pending[pkey]
                    else:
                        _pending[pkey] = (now_ts, imb, price)
                else:
                    _pending[pkey] = (now_ts, imb, price)
            for f in not_done: f.cancel()
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
        
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
                lines.append("  LONG (trend-filtered)")
                for sym, direction, imb, price, score, cv5 in longs[:3]:
                    s = sym.replace("USDT","")
                    chg24 = _trend_cache.get(sym, 0)
                    conf = "HOT" if score >= 55 else ""
                    lines.append("    %s %s %dpt $%s | 24h:%+.1f%%" % (conf, s, score, str(price), chg24))
            
            if shorts:
                lines.append("  SHORT")
                for sym, direction, imb, price, score, cv5 in shorts[:3]:
                    s = sym.replace("USDT","")
                    conf = "HOT" if score >= 55 else ""
                    lines.append("    %s %s %dpt $%s" % (conf, s, score, str(price)))
            
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