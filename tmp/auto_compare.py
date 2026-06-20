# auto_compare.py - track yaobi vs mercu accuracy over time
import urllib.request, json, time, os
from datetime import datetime, timezone, timedelta

LOG = "/home/ubuntu/scripts/agents/signal_log.json"
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
BJT = timezone(timedelta(hours=8))
seen = set()

while True:
    if not os.path.exists(LOG):
        time.sleep(60)
        continue
    
    with open(LOG) as f:
        entries = json.load(f)
    
    all_sigs = []
    for e in entries:
        src = e.get("source", "?")
        for s in e["signals"]:
            key = src + s["sym"] + s["dir"] + str(s["price"])
            all_sigs.append((e["time"], src, s["sym"], s["dir"], s["price"], key))
    
    new_keys = set(k for _,_,_,_,_,k in all_sigs)
    if new_keys == seen and seen:
        print(".", end="", flush=True)
        time.sleep(120)
        continue
    
    yw = yl = mw = ml = 0
    for t, src, sym, direction, entry, key in all_sigs:
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym + "USDT"
            data = json.loads(opener.open(url, timeout=10).read())
            curr = float(data["price"])
            pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
            if src == "mercu":
                if pnl > 0: mw += 1
                else: ml += 1
            else:
                if pnl > 0: yw += 1
                else: yl += 1
        except:
            pass
    
    yt = yw + yl
    mt = mw + ml
    now_str = datetime.now(BJT).strftime("%H:%M")
    ya_str = "Yaobi: " + str(yw) + "/" + str(yt) + "=" + str(round(yw/yt*100)) + "%" if yt > 0 else "Yaobi: --"
    mc_str = "MerCu: " + str(mw) + "/" + str(mt) + "=" + str(round(mw/mt*100)) + "%" if mt > 0 else "MerCu: --"
    print("\n[" + now_str + "] " + ya_str + " | " + mc_str + " (total " + str(yt+mt) + " sigs)")
    
    seen = new_keys
    time.sleep(120)
