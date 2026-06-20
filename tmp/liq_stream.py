#!/usr/bin/env python3
"""Binance Liquidation Tracker - WebSocket forceOrder stream"""
import sys, os, json, time, threading
from urllib.request import Request, build_opener, ProxyHandler
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import feishu_send

OUTPUT = '/home/ubuntu/scripts/agents/liquidation_cache.json'

# Track liquidations by price zone
liq_zones = {}  # symbol -> {price_zone: total_qty}
liq_events = []  # recent events
liq_lock = threading.Lock()

# Use websocket-client
try:
    from websocket import create_connection, WebSocket
except:
    os.system('pip install websocket-client -q')
    from websocket import create_connection, WebSocket

COINS = ['btcusdt','ethusdt','solusdt','bnbusdt','dogeusdt','xrpusdt']
STREAM_URL = 'wss://fstream.binance.com/ws'

def build_stream():
    streams = [f'{c}@forceOrder' for c in COINS]
    return f'{STREAM_URL}/{"".join(streams)}'

def process_liquidation(data):
    try:
        s = data.get('s', '')  # symbol
        p = float(data.get('p', 0))  # price
        q = float(data.get('q', 0))  # quantity
        side = data.get('S', '')  # SELL=long liq, BUY=short liq

        if p <= 0 or q <= 0:
            return

        # Round to nearest zone (1% for BTC/ETH, 2% for others)
        if 'BTC' in s.upper():
            zone_pct = 0.005
        elif 'ETH' in s.upper():
            zone_pct = 0.01
        else:
            zone_pct = 0.02

        zone = round(p / (p * zone_pct)) * (p * zone_pct)
        zone = round(zone, 2)

        with liq_lock:
            if s not in liq_zones:
                liq_zones[s] = {}
            liq_zones[s][zone] = liq_zones[s].get(zone, 0) + q * p

            liq_events.append({
                'symbol': s, 'price': p, 'qty': q, 'side': side,
                'time': int(time.time())
            })
            # Keep last 500 events
            if len(liq_events) > 500:
                liq_events.pop(0)

        # Big liquidation alert (>$500k)
        if q * p > 500000:
            dir_cn = '????(??)' if side == 'SELL' else '????(??)'
            emoji = '??' if side == 'SELL' else '??'
            msg = f'{emoji} {s.replace("USDT","")} ????\n'
            msg += f'${p} | ${round(q*p/1000)}k | {dir_cn}'
            feishu_send(msg)

    except Exception as e:
        pass

def save_cache():
    while True:
        time.sleep(120)  # Save every 2 min
        try:
            with liq_lock:
                cache = {}
                for sym, zones in liq_zones.items():
                    if not zones:
                        continue
                    sorted_zones = sorted(zones.items(), key=lambda x: x[1], reverse=True)
                    current_price = 0
                    try:
                        from hermes_core import fetch_price
                        current_price = fetch_price(sym)
                    except:
                        pass

                    above = {p: v for p, v in sorted_zones if p > current_price}
                    below = {p: v for p, v in sorted_zones if p < current_price}
                    cache[sym] = {
                        'above_zones': above,
                        'below_zones': below,
                        'current': current_price,
                        'total_events': len([e for e in liq_events if e['symbol'] == sym])
                    }
                with open(OUTPUT, 'w') as f:
                    json.dump(cache, f, indent=2)
        except:
            pass

def run():
    print('[LiqStream] Starting Binance liquidation tracker...')
    feishu_send('?? ??????? | Binance WebSocket forceOrder | ????????')

    # Start save thread
    t = threading.Thread(target=save_cache, daemon=True)
    t.start()

    while True:
        try:
            url = build_stream()
            print('[LiqStream] Connecting to', url[:60] + '...')
            ws = create_connection(url, timeout=30)

            while True:
                data = json.loads(ws.recv())
                if 'data' in data:
                    process_liquidation(data['data'])

        except Exception as e:
            print('[LiqStream] Error:', e)
            time.sleep(10)

if __name__ == '__main__':
    run()
