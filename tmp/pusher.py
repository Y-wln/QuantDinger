#!/usr/bin/env python3
import sys, os, time
from datetime import datetime, timezone, timedelta
BJT = timezone(timedelta(hours=8))
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_klines, fetch_price, calc_cvd, feishu_send

COINS = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT',
    'DOGEUSDT','LINKUSDT','AVAXUSDT','DOTUSDT','LTCUSDT','INJUSDT']
SCAN_INTERVAL = 15
COOLDOWN = 300
MIN_SCORE = 12
last_alert = {}

def quick_launch_score(sym):
    score = 0
    reasons = []
    k5 = fetch_klines(sym, '5m', 12)
    if len(k5) < 8:
        return 0, []
    cv5 = calc_cvd(k5, 4)
    if cv5 > 25:
        score += 8; reasons.append('5mCVD_buy_' + str(int(cv5)) + '%')
    elif cv5 < -25:
        score -= 8; reasons.append('5mCVD_sell_' + str(int(cv5)) + '%')
    elif cv5 > 12:
        score += 4
    elif cv5 < -12:
        score -= 4
    v5 = [k['v'] for k in k5]
    avg_v = sum(v5[:-1]) / max(len(v5)-1, 1)
    if avg_v > 0:
        vr = v5[-1] / avg_v
        if vr > 2.5:
            score += (6 if cv5 > 0 else -6)
            reasons.append('5m_vol_' + str(round(vr,1)) + 'x')
        elif vr > 1.5:
            score += (3 if cv5 > 0 else -3)
    c5 = [k['c'] for k in k5]
    mom = (c5[-1] - c5[0]) / c5[0] * 100
    if abs(mom) > 1.5:
        score += (6 if mom > 0 else -6)
        reasons.append('mom_' + str(round(mom,1)) + '%')
    k1m = fetch_klines(sym, '1m', 10)
    if len(k1m) >= 6:
        cv1 = calc_cvd(k1m, 4)
        if abs(cv1) > 30:
            score += (6 if cv1 > 0 else -6)
            reasons.append('1mCVD_' + str(int(cv1)) + '%')
    return score, reasons

def scan():
    for sym in COINS:
        try:
            score, reasons = quick_launch_score(sym)
            if abs(score) < MIN_SCORE:
                continue
            d = 'LONG' if score > 0 else 'SHORT'
            ck = sym + '_' + d
            if ck in last_alert and time.time() - last_alert[ck] < COOLDOWN:
                continue
            price = fetch_price(sym)
            if price <= 0:
                continue
            now = datetime.now(BJT).strftime('%H:%M:%S')
            name = sym.replace('USDT','')
            lines = [d + ' ' + name + ' launch ' + now + ' score=' + str(score)]
            for r in reasons:
                lines.append('  ' + r)
            feishu_send('\n'.join(lines))
            last_alert[ck] = time.time()
        except Exception:
            pass

if __name__ == '__main__':
    feishu_send('Signal Pusher online | 12 coins | 15s scan | min_score=' + str(MIN_SCORE))
    while True:
        try:
            scan()
        except Exception as e:
            print('err:', e)
        time.sleep(SCAN_INTERVAL)
