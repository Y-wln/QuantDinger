#!/usr/bin/env python3
"""ws_sentinel v1 - Binance WebSocket real-time anomaly detection + Feishu"""
import sys, os, time, json, threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import websocket

sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import feishu_app_send, feishu_send, proxy_mgr

BJT = timezone(timedelta(hours=8))
BINANCE_WS = 'wss://fstream.binance.com/ws'

SKIP = {'BTC','ETH','SOL','BNB','XRP','ADA','DOGE','DOT','LINK','AVAX','LTC',
    'USDC','USDT','DAI','BUSD','TUSD','FDUSD','WBTC','STETH'}

price_history = defaultdict(list)
last_alert = {}
COOLDOWN = 120
MIN_VOL = 500000

def on_message(ws, message):
    try:
        data = json.loads(message)
        if 'data' in data:
            tickers = data['data']
            now = time.time()
            for t in tickers:
                sym = t.get('s', '')
                if not sym.endswith('USDT'):
                    continue
                name = sym.replace('USDT', '')
                if name in SKIP:
                    continue
                try:
                    price = float(t.get('c', 0))
                    vol = float(t.get('q', 0))
                    if price <= 0 or vol < MIN_VOL:
                        continue
                except:
                    continue

                history = price_history[sym]
                history.append((price, now, vol))
                cutoff = now - 60
                while history and history[0][1] < cutoff:
                    history.pop(0)

                if len(history) < 5:
                    continue

                prices = [h[0] for h in history]
                price_delta_pct = (prices[-1] - prices[0]) / prices[0] * 100

                vols = [h[2] for h in history]
                avg_vol = sum(vols[:-1]) / max(len(vols)-1, 1)
                vol_surge = vols[-1] / avg_vol if avg_vol > 0 else 1

                direction = None
                reasons = []

                if price_delta_pct > 0.8 and vol_surge > 1.5:
                    direction = 'long'
                    reasons.append('sec_up_{:.1f}pct'.format(price_delta_pct))
                elif price_delta_pct < -0.8 and vol_surge > 1.5:
                    direction = 'short'
                    reasons.append('sec_down_{:.1f}pct'.format(abs(price_delta_pct)))

                if vol_surge > 3.0:
                    reasons.append('vol_{:.1f}x'.format(vol_surge))
                    if not direction:
                        direction = 'long' if price_delta_pct > 0 else 'short'

                if not direction:
                    continue

                ck = sym + '_' + direction
                if ck in last_alert and now - last_alert[ck] < COOLDOWN:
                    continue

                if direction == 'long' and price_delta_pct > 3.0:
                    reasons.append('WARN_extended')
                if direction == 'short' and price_delta_pct < -3.0:
                    reasons.append('WARN_extended')

                last_alert[ck] = now
                t_str = datetime.now(BJT).strftime('%H:%M:%S')
                emoji = '\U0001f7e2' if direction == 'long' else '\U0001f534'
                dir_cn = 'LONG' if direction == 'long' else 'SHORT'
                cn = sym.replace('USDT', '')
                p_str = '${:.4f}'.format(price)

                msg = '\u2501' * 22 + '\n'
                msg += '  \u26a1 WS_REALTIME | ' + t_str + '\n'
                msg += '  {} {} {} | {}\n'.format(emoji, cn, dir_cn, p_str)
                msg += '  \u2192 ' + ' | '.join(reasons) + '\n'
                msg += '  \u2501' * 22

                feishu_app_send(msg)

    except Exception:
        pass

def on_error(ws, error):
    print('ws error:', error)

def on_close(ws, close_status_code, close_msg):
    print('ws closed, reconnect in 3s...')
    time.sleep(3)
    start_ws()

def on_open(ws):
    sub = {'method': 'SUBSCRIBE', 'params': ['!miniTicker@arr'], 'id': 1}
    ws.send(json.dumps(sub))
    print('ws subscribed')

def start_ws():
    ws = websocket.WebSocketApp(
        BINANCE_WS,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever(
        http_proxy_host='127.0.0.1',
        http_proxy_port=7891,
        ping_interval=30,
        ping_timeout=10
    )

if __name__ == '__main__':
    t0 = datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
    print('ws_sentinel v1 start |', t0)
    feishu_send('\u26a1 WS_REALTIME_SENTINEL online | 0.8pct+1.5x_vol | all_coins')
    while True:
        try:
            start_ws()
        except Exception as e:
            print('ws crash:', e)
            time.sleep(5)
