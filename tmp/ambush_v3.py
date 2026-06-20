# ambush_scanner.py v3 - PRIMARY signal source, OB-predictive
import sys, os, time, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
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

_pending = {}     # sym_dir -> (ts, imb, price)
_alerted = {}     # sym_dir -> alert_ts
_last_score = {}  # sym_dir -> score for confidence tracking

print("[Ambush v3 PRIMARY] OB-predictive signal source starting...")
feishu_app_send("Ambush v3 PRIMARY | 15s OB + CVD-confirm | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

while True:
    try:
        t0 = time.time()
        now_ts = time.time()
        signals = []
        
        def scan_coin(sym):
            try:
                ob = fetch_orderbook_imbalance(sym, 100)
                if not ob: return None
                imb = ob.get("imbalance", 0)
                if abs(imb) < 22: return None
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
                        # Confirmed! 2nd sighting
                        avg_imb = (abs(imb) + abs(prev_imb)) // 2
                        
                        # CVD quick check
                        cv5 = 0
                        try:
                            k5 = fetch_klines(sym, "5m", 30)
                            if k5: cv5 = calc_cvd(k5, 3)
                        except: pass
                        
                        # Score: OB strength + CVD alignment + persistence
                        score = avg_imb
                        if (direction == "long" and cv5 > 10) or (direction == "short" and cv5 < -10):
                            score += 10  # CVD confirms
                        elif (direction == "long" and cv5 < 0) or (direction == "short" and cv5 > 0):
                            score -= 15  # CVD opposes -> weaker
                        
                        # Track score trend
                        prev_score = _last_score.get(pkey, 0)
                        if score > prev_score:
                            score += 5  # strengthening
                        _last_score[pkey] = score
                        
                        # Only push if score >= 25
                        if score >= 25:
                            signals.append((sym, direction, avg_imb, price, score, cv5))
                            _alerted[pkey] = now_ts
                        del _pending[pkey]
                    else:
                        _pending[pkey] = (now_ts, imb, price)
                else:
                    _pending[pkey] = (now_ts, imb, price)
        
        # Clean stale pending
        for key in list(_pending.keys()):
            if now_ts - _pending[key][0] > 90:
                del _pending[key]
        
        if signals:
            signals.sort(key=lambda x: -x[4])
            t = datetime.now(BJT).strftime("%m/%d %H:%M")
            lines = ["----------------", "  \U0001f3af Ambush V3 | %s" % t, "----------------"]
            
            longs = [s for s in signals if s[1] == "long"]
            shorts = [s for s in signals if s[1] == "short"]
            
            if longs:
                lines.append("  \U0001f7e2 LONG")
                for sym, direction, imb, price, score, cv5 in longs[:4]:
                    sym_s = sym.replace("USDT","")
                    conf = "\U0001f525" if score >= 40 else ("\U0001f4ca" if score >= 30 else "")
                    cv5_str = " CVD:" + ("+%d" % cv5 if cv5 > 0 else "%d" % cv5) if abs(cv5) > 5 else ""
                    lines.append("    %s %s %dpt %s $%s%s" % (conf, sym_s, score, "OB:%+d%%" % imb, str(price), cv5_str))
            
            if shorts:
                lines.append("  \U0001f534 SHORT")
                for sym, direction, imb, price, score, cv5 in shorts[:4]:
                    sym_s = sym.replace("USDT","")
                    conf = "\U0001f525" if score >= 40 else ("\U0001f4ca" if score >= 30 else "")
                    cv5_str = " CVD:" + ("+%d" % cv5 if cv5 > 0 else "%d" % cv5) if abs(cv5) > 5 else ""
                    lines.append("    %s %s %dpt %s $%s%s" % (conf, sym_s, score, "OB:%+d%%" % imb, str(price), cv5_str))
            
            lines.append("----------------")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
            print("[AmbushV3] %d signals (L:%d S:%d)" % (len(signals), len(longs), len(shorts)))
        
        elapsed = time.time() - t0
        time.sleep(max(3, 15 - elapsed))
    except Exception as e:
        print("[AmbushV3] error:", e)
        time.sleep(15)
