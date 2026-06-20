# auto_compare_v2.py - always-print version
import urllib.request, json, time, os
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
LOG = "/home/ubuntu/scripts/agents/signal_log.json"

SOURCES = ["ambush","yaobi","mercu","reversal","surge"]

while True:
    if not os.path.exists(LOG): time.sleep(60); continue
    with open(LOG) as f: entries = json.load(f)
    
    all_sigs = []
    for e in entries:
        src = e.get("source","?")
        for s in e["signals"]:
            all_sigs.append((src, s["sym"], s["dir"], s["price"]))
    
    wins = {s:0 for s in SOURCES}
    total = {s:0 for s in SOURCES}
    for src, sym, direction, entry_price in all_sigs:
        if src not in total: total[src]=0; wins[src]=0
        total[src] += 1
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym + "USDT"
            curr = float(json.loads(opener.open(url,timeout=10).read())["price"])
            pnl = (curr-entry_price)/entry_price*100 if direction=="long" else (entry_price-curr)/entry_price*100
            if pnl > 0: wins[src] += 1
        except: pass
    
    def pct(src):
        t = total.get(src,0)
        return str(round(wins.get(src,0)/t*100))+"%" if t>0 else "--"
    
    parts = []
    for s in SOURCES:
        t = total.get(s,0)
        if t > 0:
            parts.append("%s:%s(%d)" % (s[:4].title(), pct(s), t))
    
    now = int(time.time()/60) % 1440
    print("\n[%02d:%02d] %s" % (now//60, now%60, " | ".join(parts)))
    time.sleep(60)