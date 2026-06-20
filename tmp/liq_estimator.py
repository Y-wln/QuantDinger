#!/usr/bin/env python3
"""?????? - ??????+???????????API"""
import sys, os, json, time
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_klines, fetch_price

OUTPUT = '/home/ubuntu/scripts/agents/liquidation_cache.json'

def estimate_liquidation_zones(symbol):
    """Estimate liquidation zones from volume profile and price extremes"""
    k4 = fetch_klines(symbol, '4h', 100)
    k1 = fetch_klines(symbol, '1h', 200)
    price = fetch_price(symbol)

    if len(k4) < 20 or price <= 0:
        return None

    # 1. Volume profile: find high-volume price zones (liquidation magnets)
    closes = [k['c'] for k in k4[-50:]]
    highs = [k['h'] for k in k4[-50:]]
    lows = [k['l'] for k in k4[-50:]]
    volumes = [k['v'] for k in k4[-50:]]

    all_prices = highs + lows
    all_prices.sort()
    current = price

    # Split into above/below current price
    above_zones = []
    below_zones = []
    for i, k in enumerate(k4[-30:]):
        v = volumes[-(30-i)] if i < len(volumes) else volumes[-1]
        h = k['h']
        l = k['l']
        if h > current:
            above_zones.append((h, v))
        if l < current:
            below_zones.append((l, v))

    # Sort by volume
    above_zones.sort(key=lambda x: x[1], reverse=True)
    below_zones.sort(key=lambda x: x[1], reverse=True)

    # 2. Recent swing points (where stops cluster)
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    range_size = recent_high - recent_low

    above = {
        'zones': [{'price': round(z[0], 4), 'volume': round(z[1], 0)} for z in above_zones[:3]],
        'key_level': round(recent_high, 4),
        'value': round(sum(z[1] for z in above_zones[:3]), 0)
    }
    below = {
        'zones': [{'price': round(z[0], 4), 'volume': round(z[1], 0)} for z in below_zones[:3]],
        'key_level': round(recent_low, 4),
        'value': round(sum(z[1] for z in below_zones[:3]), 0)
    }

    total = above['value'] + below['value']
    return {'above': above, 'below': below, 'current': price,
            'ratio_above': round(above['value'] / max(total, 1), 2),
            'range_pct': round(range_size / price * 100, 2)}

def update_cache():
    coins = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','DOGEUSDT','LINKUSDT','AVAXUSDT','DOTUSDT']
    cache = {}
    for sym in coins:
        try:
            zones = estimate_liquidation_zones(sym)
            if zones:
                cache[sym] = zones
        except:
            pass
    with open(OUTPUT, 'w') as f:
        json.dump(cache, f, indent=2)

if __name__ == '__main__':
    while True:
        try:
            update_cache()
            print('[' + time.strftime('%H:%M:%S') + '] Liquidation cache updated: ' + str(len(open(OUTPUT).read())) + ' bytes')
        except Exception as e:
            print('err:', e)
        time.sleep(300)  # every 5 min
