# auto_compare_v2.py - track ambush + yaobi + mercu
import urllib.request, json, time, os
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
LOG = "/home/ubuntu/scripts/agents/signal_log.json"
seen = set()

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
    
    wins = {"ambush":0,"yaobi":0,"mercu":0}
    total = {"ambush":0,"yaobi":0,"mercu":0}
    for src, sym, direction, entry, key in all_sigs:
        total[src] = total.get(src,0) + 1
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym + "USDT"
            curr = float(json.loads(opener.open(url,timeout=10).read())["price"])
            pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
            if pnl > 0: wins[src] = wins.get(src,0) + 1
        except: pass
    
    def pct(src):
        t = total.get(src,0)
        return str(round(wins.get(src,0)/t*100)) + "%" if t>0 else "--"
    
    print("\n[17:%02d] Ambush:%s(%d) Yaobi:%s(%d) MerCu:%s(%d)" % (
        int(time.time()%3600/60), pct("ambush"), total.get("ambush",0),
        pct("yaobi"), total.get("yaobi",0), pct("mercu"), total.get("mercu",0)))
    seen = new_keys
    time.sleep(120)
