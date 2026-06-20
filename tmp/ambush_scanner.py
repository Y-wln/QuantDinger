# ambush_scanner.py v1 - pre-signal OB ambush alerts
# Monitors orderbook imbalance for early positioning
# Runs independently: 15s cycle, OB-only, no CVD wait

import sys, os, time, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_orderbook_imbalance, feishu_app_send, fetch_price
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BJT = timezone(timedelta(hours=8))
CHAT_ID = "oc_58c90b36ddb0d64439c64ed83a16b47b"

# All yaobi coins + mainstream
COINS = ["CHZUSDT","IOUSDT","TONUSDT","STRAXUSDT","SENTUSDT","ENAUSDT","UNIUSDT",
    "TAOUSDT","ONDOUSDT","PUMPUSDT","ALLOUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT",
    "BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","BNBUSDT","XRPUSDT","ADAUSDT","AVAXUSDT",
    "LINKUSDT","LTCUSDT","DOTUSDT"]

_alerted = {}  # sym_dir -> timestamp, avoid spam

print("[Ambush v1] OB ambush scanner starting...")
feishu_app_send("Ambush Scanner v1 | 15s OB monitor | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

while True:
    try:
        t0 = time.time()
        now_ts = time.time()
        alerts = []
        
        def check_ob(sym):
            try:
                ob = fetch_orderbook_imbalance(sym, 100)
                if not ob: return None
                imb = ob.get("imbalance", 0)
                if abs(imb) < 28: return None  # threshold for alert
                
                key = sym + ("_BID" if imb > 0 else "_ASK")
                last = _alerted.get(key, 0)
                if now_ts - last < 300: return None  # 5min cooldown
                
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
                    sym_short = sym.replace("USDT", "")
                    direction = "LONG" if imb > 0 else "SHORT"
                    alerts.append((sym_short, direction, imb, price))
                    _alerted[sym + ("_BID" if imb > 0 else "_ASK")] = now_ts
        
        if alerts:
            alerts.sort(key=lambda x: -abs(x[2]))
            t = datetime.now(BJT).strftime("%H:%M")
            lines = ["----------------", "  \u23f3 Ambush OB Alert | %s" % t, "----------------"]
            for sym, direction, imb, price in alerts[:5]:
                icon = "\U0001f7e2" if direction == "LONG" else "\U0001f534"
                lines.append("  %s %s %s %+d%% @%s" % (icon, sym, direction, imb, price))
            lines.append("----------------")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
            print("[Ambush] %d alerts: %s" % (len(alerts), ", ".join("%s(%+d%%)" % (a[0], a[2]) for a in alerts[:3])))
        
        elapsed = time.time() - t0
        time.sleep(max(3, 15 - elapsed))
    except Exception as e:
        print("[Ambush] error:", e)
        time.sleep(15)
