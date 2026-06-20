#!/usr/bin/env python3
import sys, os, json, time, re
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import feishu_send, fetch_klines, fetch_price
from urllib.request import Request, build_opener, ProxyHandler

ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)
OUTPUT = "/home/ubuntu/scripts/agents/liquidation_cache.json"
COINS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT"]

def est_liq(symbol):
    k4 = fetch_klines(symbol, "4h", 50)
    price = fetch_price(symbol)
    if len(k4) < 20 or price <= 0:
        return None
    highs = [k["h"] for k in k4[-20:]]
    lows = [k["l"] for k in k4[-20:]]
    vols = [k["v"] for k in k4[-20:]]
    above = sum(v for i, v in enumerate(vols) if highs[i] > price)
    below = sum(v for i, v in enumerate(vols) if lows[i] < price)
    return {
        "above": {"key": round(max(highs), 4), "vol": round(above, 0)},
        "below": {"key": round(min(lows), 4), "vol": round(below, 0)},
        "ratio": round(above / max(above + below, 1), 2)
    }

def fetch_news():
    items = []
    for url in ["https://decrypt.co/feed", "https://cointelegraph.com/rss"]:
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with opener.open(req, timeout=12) as resp:
                c = resp.read().decode("utf-8", errors="ignore")
            found = re.findall(r"<item>.*?<title>(.*?)</title>.*?</item>", c, re.DOTALL)
            for t in found[:5]:
                t = re.sub(r"<[^>]+>", "", t).strip()
                if len(t) > 10:
                    items.append(t)
        except:
            pass
    return items[:6]

last_news = set()

if __name__ == "__main__":
    cache = {}
    for s in COINS:
        z = est_liq(s)
        if z:
            cache[s] = z
    with open(OUTPUT, "w") as f:
        json.dump(cache, f)
    print("Liq+News started")
    feishu_send("Liq+News online")

    while True:
        try:
            cache = {}
            for s in COINS:
                z = est_liq(s)
                if z:
                    cache[s] = z
            with open(OUTPUT, "w") as f:
                json.dump(cache, f)
            headlines = fetch_news()
            new = [h for h in headlines if h not in last_news]
            if new:
                msg = "News\n" + "\n".join("  " + h[:80] for h in new[:4])
                feishu_send(msg)
            last_news = set(headlines)
            print("[" + time.strftime("%H:%M:%S") + "] Liq+News OK")
        except Exception as e:
            print("err:", e)
        time.sleep(120)
