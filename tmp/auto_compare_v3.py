# auto_compare_v2.py - track ambush + yaobi + mercu + reversal
import urllib.request, json, time, os
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
LOG = "/home/ubuntu/scripts/agents/signal_log.json"
seen = set()

SOURCES = ["ambush","yaobi","mercu","reversal"]

while True:
    if not os.path.exists(LOG): time.sleep(60); continue
    with open(LOG) as f: entries = json.load(f)
    
    all_sigs = []
    for e in entries:
        src = e.get("source","?")
        for s in e["signals"]:
            key = src + s["sym"] + s["dir"] + str(s["price"])
            all_sigs.append((src, s["sym"], s["dir"], s["price"], key))
    
    new_keys = set(k for _,_,_,_,k in all_sigs)
    if new_keys == seen and seen:
        print(".", end="", flush=True)
        time.sleep(120); continue
    
    wins = {s:0 for s in SOURCES}
    total = {s:0 for s in SOURCES}
    for src, sym, direction, entry_price, key in all_sigs:
        if src not in total: total[src] = 0; wins[src] = 0
        total[src] += 1
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym + "USDT"
            curr = float(json.loads(opener.open(url,timeout=10).read())["price"])
            pnl = round((curr-entry_price)/entry_price*100,2) if direction=="long" else round((entry_price-curr)/entry_price*100,2)
            if pnl > 0: wins[src] += 1
        except: pass
    
    def pct(src):
        t = total.get(src,0)
        return str(round(wins.get(src,0)/t*100)) + "%" if t>0 else "--"
    
    parts = []
    for s in SOURCES:
        parts.append("%s:%s(%d)" % (s[:4].title(), pct(s), total.get(s,0)))
    
    print("\n[%02d:%02d] %s" % (int(time.time()/3600)%24, int(time.time()%3600/60), " | ".join(parts)))
    seen = new_keys
    time.sleep(120)