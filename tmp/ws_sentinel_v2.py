#!/usr/bin/env python3
"""ws_sentinel v2 - 高频REST轮询版 (2s一轮全币种价格)"""
import sys, os, time, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import feishu_app_send, feishu_send, proxy_mgr, BINANCE_F

BJT = timezone(timedelta(hours=8))

SKIP = {'BTC','ETH','SOL','BNB','XRP','ADA','DOGE','DOT','LINK','AVAX','LTC',
    'USDC','USDT','DAI','BUSD','TUSD','FDUSD','WBTC','STETH'}

price_history = defaultdict(list)
last_alert = {}
COOLDOWN = 90
MIN_VOL = 300000

def scan():
    try:
        data = proxy_mgr.fetch_json(BINANCE_F + '/fapi/v1/ticker/24hr', 5)
        if not data:
            return

        now = time.time()
        alerts = []

        for t in data:
            sym = t.get('symbol', '')
            if not sym.endswith('USDT'):
                continue
            name = sym.replace('USDT', '')
            if name in SKIP:
                continue
            try:
                price = float(t.get('lastPrice', 0))
                vol = float(t.get('quoteVolume', 0))
                chg = float(t.get('priceChangePercent', 0))
                if price <= 0 or vol < MIN_VOL:
                    continue
            except:
                continue

            # Track price history (last 30 seconds)
            history = price_history[sym]
            history.append((price, now, vol))
            cutoff = now - 30
            while history and history[0][1] < cutoff:
                history.pop(0)

            if len(history) < 4:
                continue

            prices = [h[0] for h in history]
            price_30s = (prices[-1] - prices[0]) / prices[0] * 100
            price_5s = (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) >= 2 else 0

            vols = [h[2] for h in history]
            avg_vol = sum(vols[:-1]) / max(len(vols)-1, 1)
            vol_surge = vols[-1] / avg_vol if avg_vol > 0 else 1

            direction = None
            reasons = []

            # Strong directional move + volume
            if price_30s > 0.5 and vol_surge > 1.3:
                direction = 'LONG'; reasons.append('30s+{:.1f}%'.format(price_30s))
            elif price_30s < -0.5 and vol_surge > 1.3:
                direction = 'SHORT'; reasons.append('30s-{:.1f}%'.format(abs(price_30s)))

            if price_5s > 0.3:
                if not direction: direction = 'LONG'
                reasons.append('5s+{:.1f}%'.format(price_5s))
            elif price_5s < -0.3:
                if not direction: direction = 'SHORT'
                reasons.append('5s-{:.1f}%'.format(abs(price_5s)))

            if vol_surge > 2.5:
                reasons.append('vol{:.1f}x'.format(vol_surge))
                if not direction:
                    direction = 'LONG' if price_30s > 0 else 'SHORT'

            if not direction:
                continue

            ck = sym + '_' + direction
            if ck in last_alert and now - last_alert[ck] < COOLDOWN:
                continue

            last_alert[ck] = now
            cn = sym.replace('USDT', '')
            alerts.append((cn, direction, price, chg, reasons))

        # Send top 3 alerts
        alerts.sort(key=lambda x: abs(float(x[3])), reverse=True)
        for cn, direction, price, chg, reasons in alerts[:3]:
            t_str = datetime.now(BJT).strftime('%H:%M:%S')
            emoji = '\U0001f7e2' if direction == 'LONG' else '\U0001f534'
            dir_cn = '做多' if direction == 'LONG' else '做空'

            lines = [
                '\u2501' * 22,
                '  \u26a1 秒级异动 | ' + t_str,
                '  {} {} {} | ${:.4f} | 24h:{:+.1f}%'.format(emoji, cn, dir_cn, price, chg),
                '  \u2192 ' + ' | '.join(reasons[:4]),
                '\u2501' * 22
            ]
            feishu_app_send('\n'.join(lines))

    except Exception as e:
        print('scan err:', e)

if __name__ == '__main__':
    t0 = datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')
    print('sentinel v2 (REST 2s) start |', t0)
    feishu_send('\u26a1 秒级异动监控上线 | 2s轮询全币种 | 30s价格+放量检测')
    while True:
        t_start = time.time()
        scan()
        elapsed = time.time() - t_start
        sleep_time = max(1, 2 - elapsed)
        time.sleep(sleep_time)
