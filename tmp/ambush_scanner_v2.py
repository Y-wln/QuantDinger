# ambush_scanner.py v2 - persistence filter against spoofing
import sys, os, time, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_orderbook_imbalance, feishu_app_send, fetch_price
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BJT = timezone(timedelta(hours=8))
CHAT_ID = "oc_58c90b36ddb0d64439c64ed83a16b47b"

COINS = ["CHZUSDT","IOUSDT","TONUSDT","STRAXUSDT","SENTUSDT","ENAUSDT","UNIUSDT",
    "TAOUSDT","ONDOUSDT","PUMPUSDT","ALLOUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT",
    "BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","BNBUSDT","XRPUSDT","ADAUSDT","AVAXUSDT",
    "LINKUSDT","LTCUSDT","DOTUSDT"]

_alerted = {}     # sym_dir -> alert timestamp
_pending = {}     # sym_dir -> (first_seen_ts, imb, price) - wait for 2nd confirm
PERSIST_SCANS = 2  # need 2 consecutive scans before alerting

print("[Ambush v2] OB + persistence filter starting...")
feishu_app_send("Ambush Scanner v2 | 15s OB + persistence x2 | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

while True:
    try:
        t0 = time.time()
        now_ts = time.time()
        alerts = []
        current_obs = {}  # sym -> imb
        
        def check_ob(sym):
            try:
                ob = fetch_orderbook_imbalance(sym, 100)
                if not ob: return None
                imb = ob.get("imbalance", 0)
                if abs(imb) < 25: return None
                price = fetch_price(sym)
                return (sym, imb, price)
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(check_ob, s): s for s in COINS}
            for f in as_completed(futures, timeout=25):
                r = f.result()
                if r:
                    sym, imb, price = r
                    current_obs[sym] = imb
                    sym_short = sym.replace("USDT", "")
                    direction = "LONG" if imb > 0 else "SHORT"
                    pkey = sym + "_" + direction
                    
                    # Check if we saw this direction last scan
                    if pkey in _pending:
                        prev_ts, prev_imb, prev_price = _pending[pkey]
                        # Confirm: same direction, and not too stale (<60s)
                        if now_ts - prev_ts < 60:
                            # Alert!
                            avg_imb = int((abs(imb) + abs(prev_imb)) / 2)
                            alerts.append((sym_short, direction, avg_imb, price, "confirmed"))
                            _alerted[pkey] = now_ts
                            del _pending[pkey]
                        else:
                            # Too old, restart
                            _pending[pkey] = (now_ts, imb, price)
                    else:
                        # First sighting, store for next scan
                        _pending[pkey] = (now_ts, imb, price)
        
        # Clear stale pending (>90s old)
        for key in list(_pending.keys()):
            if now_ts - _pending[key][0] > 90:
                del _pending[key]
        
        if alerts:
            alerts.sort(key=lambda x: -x[2])
            t = datetime.now(BJT).strftime("%H:%M")
            lines = ["----------------", "  \u23f3 Ambush V2 | %s" % t, "----------------"]
            for sym, direction, imb, price, status in alerts[:5]:
                icon = "\U0001f7e2" if direction == "LONG" else "\U0001f534"
                lines.append("  %s %s %s %+d%% @%s" % (icon, sym, direction, imb, price))
            lines.append("----------------")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
            print("[AmbushV2] %d confirmed: %s" % (len(alerts), ", ".join("%s(%+d%%)" % (a[0], a[2]) for a in alerts[:3])))
        
        elapsed = time.time() - t0
        time.sleep(max(3, 15 - elapsed))
    except Exception as e:
        print("[AmbushV2] error:", e)
        time.sleep(15)
