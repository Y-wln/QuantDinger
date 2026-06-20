import urllib.request, json, time, os

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
LOG = "/home/ubuntu/scripts/agents/signal_log.json"
SOURCES = ["ambush","yaobi","mercu","reversal","surge"]
price_cache = {}

def get_price(sym):
    if sym in price_cache and time.time() - price_cache[sym][1] < 30:
        return price_cache[sym][0]
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym + "USDT"
        p = float(json.loads(opener.open(url,timeout=5).read())["price"])
        price_cache[sym] = (p, time.time())
        return p
    except:
        return None

while True:
    try:
        if not os.path.exists(LOG):
            time.sleep(30)
            continue
        with open(LOG) as f:
            entries = json.load(f)
        recent = entries[-100:]
        wins = {s: 0 for s in SOURCES}
        total = {s: 0 for s in SOURCES}
        for e in recent:
            src = e.get("source", "?")
            if src not in total:
                continue
            for s in e["signals"]:
                total[src] += 1
                curr = get_price(s["sym"])
                if curr is None:
                    continue
                pnl = (curr - s["price"]) / s["price"] * 100 if s["dir"] == "long" else (s["price"] - curr) / s["price"] * 100
                if pnl > 0:
                    wins[src] += 1
        parts = []
        for src in SOURCES:
            t = total.get(src, 0)
            if t > 0:
                parts.append("{}:{}({})".format(src[:4].title(), str(round(wins[src]/t*100))+"%", t))
        line = "[{}] {}".format(time.strftime("%H:%M"), " | ".join(parts))
        print(line, flush=True)
        with open("/tmp/tracker.log", "a") as f:
            f.write(line + "\n")
        time.sleep(60)
    except Exception as ex:
        print("ERR:", ex, flush=True)
        time.sleep(30)