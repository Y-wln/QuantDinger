#!/usr/bin/env python3
"""Liquidation + News Tracker - REST polling"""
import sys, os, json, time, re
from datetime import datetime
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import proxy_mgr, BINANCE_F, feishu_send
from urllib.request import Request, urlopen, build_opener, ProxyHandler

OUTPUT = '/home/ubuntu/scripts/agents/liquidation_cache.json'
COINS = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','DOGEUSDT','XRPUSDT']

def fetch_liquidations(symbol, limit=20):
    try:
        url = BINANCE_F + '/fapi/v1/forceOrders?symbol=' + symbol + '&limit=' + str(limit)
        data = proxy_mgr.fetch_json(url, 8)
        return data if data else []
    except:
        return []

def update_liq_cache():
    cache = {}
    for sym in COINS:
        try:
            orders = fetch_liquidations(sym, 20)
            if not orders:
                continue
            zones = {}
            for o in orders:
                try:
                    price = float(o.get('price', 0))
                    qty = float(o.get('executedQty', 0))
                    if price <= 0 or qty <= 0:
                        continue
                    zone = round(price, -1) if sym == 'BTCUSDT' else round(price, 0)
                    zones[str(zone)] = zones.get(str(zone), 0) + qty * price
                except:
                    pass
            cache[sym] = {'zones': dict(sorted(zones.items(), key=lambda x: x[1], reverse=True)[:8]),
                          'total': len(orders)}
        except:
            pass
    with open(OUTPUT, 'w') as f:
        json.dump(cache, f, indent=2)
    return len(cache)

def fetch_news():
    ph = ProxyHandler({'http':'http://127.0.0.1:7892','https':'http://127.0.0.1:7892'})
    opener = build_opener(ph)
    headlines = []
    feeds = ['https://decrypt.co/feed', 'https://cointelegraph.com/rss']
    for url in feeds:
        try:
            req = Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with opener.open(req, timeout=10) as resp:
                content = resp.read().decode('utf-8', errors='ignore')
            items = re.findall(r'<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?</item>', content, re.DOTALL)
            if not items:
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
    print('Liq+News started. Coins:', n)
    feishu_send('Liq+News online | REST polling | 2 RSS feeds')

    while True:
        try:
            t0 = time.time()
            n = update_liq_cache()

            if time.time() - last_news_ts > 600:
                last_news_ts = time.time()
                headlines = fetch_news()
                new = [h for h in headlines if h not in last_news]
                if new:
                    msg = 'News\n' + chr(10).join('  - ' + h[:80] for h in new[:4])
                    feishu_send(msg)
                last_news = set(headlines)

            print('[%s] Liq:%d coins News:checked (%.1fs)' % (time.strftime('%H:%M:%S'), n, time.time()-t0))
        except Exception as e:
            print('err:', e)
        time.sleep(120)
