#!/usr/bin/env python3
"""sentinel v3 - ultra-light REST polling"""
import sys, os, time, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import feishu_app_send, feishu_send, proxy_mgr, BINANCE_F

BJT = timezone(timedelta(hours=8))
SKIP = {'BTC','ETH','SOL','BNB','XRP','ADA','DOGE','DOT','LINK','AVAX','LTC',
    'USDC','USDT','DAI','BUSD','TUSD','FDUSD','WBTC','STETH'}

price_history = {}
last_alert = {}
COOLDOWN = 90

def scan():
    try:
        data = proxy_mgr.fetch_json(BINANCE_F + '/fapi/v1/ticker/price', 4)
        if not data:
            return
        now = time.time()
        for t in data:
            sym = t.get('symbol','')
            if not sym.endswith('USDT'):
                continue
            name = sym.replace('USDT','')
            if name in SKIP:
                continue
            try:
                price = float(t.get('price',0))
                if price <= 0:
                    continue
            except:
                continue

            if sym not in price_history:
                price_history[sym] = []
            hist = price_history[sym]
            hist.append((price, now))
            while hist and hist[0][1] < now - 10:
                hist.pop(0)
            if len(hist) < 4:
                continue

            prices = [h[0] for h in hist]
            chg_pct = (prices[-1] - prices[0]) / prices[0] * 100

            if abs(chg_pct) < 0.6:
                continue

            direction = 'LONG' if chg_pct > 0 else 'SHORT'
            ck = sym + '_' + direction
            if ck in last_alert and now - last_alert[ck] < COOLDOWN:
                continue

            last_alert[ck] = now
            cn = sym.replace('USDT','')
            emoji = '\U0001f7e2' if direction == 'LONG' else '\U0001f534'
            dir_cn = '做多' if direction == 'LONG' else '做空'
            t_str = datetime.now(BJT).strftime('%H:%M:%S')
            p_str = str(round(price, 4))

            lines = [
                '\u2501' * 20,
                '  \u26a1 秒级异动 | ' + t_str,
                '  ' + emoji + ' ' + cn + ' ' + dir_cn + ' | ' + p_str,
                '  \u2192 10s变动: ' + str(round(chg_pct, 1)) + '%',
                '\u2501' * 20
            ]
            feishu_app_send('\n'.join(lines))
    except Exception as e:
        pass

if __name__ == '__main__':
    print('sentinel v3 start |', datetime.now(BJT).strftime('%H:%M:%S'))
    feishu_send('\u26a1 秒级异动v3上线 | 2s轮询 | 0.6%/10s触发')
    while True:
        t0 = time.time()
        scan()
        dt = time.time() - t0
        time.sleep(max(0.5, 2 - dt))
