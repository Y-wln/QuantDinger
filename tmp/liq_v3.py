#!/usr/bin/env python3
"""Liquidation + News Tracker - Binance API with signing"""
import sys, os, json, time, re, hmac, hashlib
from datetime import datetime
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import feishu_send
from urllib.request import Request, build_opener, ProxyHandler

API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"
BINANCE_F = "https://fapi.binance.com"

ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)
OUTPUT = '/home/ubuntu/scripts/agents/liquidation_cache.json'
COINS = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT','XRPUSDT']

def signed_request(path, params=""):
    ts = str(int(time.time() * 1000))
    query = params + "&timestamp=" + ts if params else "timestamp=" + ts
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = BINANCE_F + path + "?" + query + "&signature=" + signature
    req = Request(url, headers={"X-MBX-APIKEY": API_KEY, "User-Agent": "Mozilla/5.0"})
    try:
        with opener.open(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return []

def fetch_liquidations(symbol):
    orders = signed_request("/fapi/v1/forceOrders", "symbol=" + symbol + "&limit=30")
    if not orders:
        return []
    return orders

def update_liq_cache():
    cache = {}
    for sym in COINS:
        try:
            orders = fetch_liquidations(sym)
            if not orders:
                continue
            zones = {}
            for o in orders:
                try:
                    price = float(o.get('price', 0))
                    qty = float(o.get('executedQty', 0))
                    side = o.get('side', '')
                    if price <= 0 or qty <= 0:
                        continue
                    zone = str(round(price, -1)) if sym == 'BTCUSDT' else str(round(price, 0))
                    zones[zone] = zones.get(zone, 0) + qty * price
                except:
                    pass
            cache[sym] = {
                'zones': dict(sorted(zones.items(), key=lambda x: x[1], reverse=True)[:8]),
                'total': len(orders)
            }
        except Exception as e:
            print("Liq err:", sym, e)
    if cache:
        with open(OUTPUT, 'w') as f:
            json.dump(cache, f, indent=2)
    return len(cache)

# News
def fetch_news():
    headlines = []
    feeds = ["https://decrypt.co/feed", "https://cointelegraph.com/rss"]
    for url in feeds:
        try:
            req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with opener.open(req, timeout=12) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
            items = re.findall(r'<item>.*?<title>(.*?)</title>.*?</item>', content, re.DOTALL)
            for title in items[:5]:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if title and len(title) > 10:
                    headlines.append(title)
        except:
            pass
    return headlines[:6]

last_news = set()
last_news_ts = 0

if __name__ == '__main__':
    n = update_liq_cache()
    print('Liq+News v3 started. Coins:', n)
    feishu_send('Liq+News v3 online | Binance signed API | 2 RSS feeds')

    while True:
        try:
            t0 = time.time()
            n = update_liq_cache()

            if time.time() - last_news_ts > 600:
                last_news_ts = time.time()
                headlines = fetch_news()
                new = [h for h in headlines if h not in last_news]
                if new:
                    msg = "News\n" + "\n".join("  " + h[:80] for h in new[:4])
                    feishu_send(msg)
                last_news = set(headlines)

            print('[%s] Liq:%d coins News:checked (%.1fs)' % (time.strftime('%H:%M:%S'), n, time.time()-t0))
        except Exception as e:
            print('err:', e)
        time.sleep(120)
