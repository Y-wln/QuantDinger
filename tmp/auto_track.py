# auto_track.py - periodic accuracy check
import urllib.request, json, time, os

LOG = "/home/ubuntu/scripts/agents/signal_log.json"
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
seen = set()

while True:
    if not os.path.exists(LOG):
        time.sleep(120)
        continue
    
    with open(LOG) as f:
        entries = json.load(f)
    
    all_sigs = []
    for e in entries:
        for s in e["signals"]:
            key = s["sym"] + s["dir"] + str(s["price"])
            all_sigs.append((e["time"], s["sym"], s["dir"], s["price"], key))
    
    if len(all_sigs) == len(seen):
        print(".", end="", flush=True)
        time.sleep(120)
        continue
    
    wins = 0
    total = 0
    for t, sym, direction, entry, key in all_sigs:
        total += 1
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym + "USDT"
            data = json.loads(opener.open(url, timeout=10).read())
            curr = float(data["price"])
            pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
            if pnl > 0: wins += 1
        except:
            pass
    
    if total > 0:
        print("\n[" + str(len(all_sigs)) + " sigs] " + str(wins) + "/" + str(total) + " = " + str(round(wins/total*100)) + "% accuracy")
    
    seen = set(k for _,_,_,_,k in all_sigs)
    time.sleep(120)
