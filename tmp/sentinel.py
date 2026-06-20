#!/usr/bin/env python3
"""Yaobi Sentinel - 10s fast scan for??"""
import sys, os, time, json
from datetime import datetime, timezone, timedelta
BJT = timezone(timedelta(hours=8))
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import (proxy_mgr, BINANCE, feishu_send,
    fetch_orderbook_imbalance, fetch_1m_cvd, fetch_klines, calc_cvd)

SKIP = {'BTC','ETH','SOL','BNB','XRP','ADA','DOGE','DOT','LINK','AVAX','LTC',
    'USDC','USDT','DAI','BUSD','TUSD','FDUSD','WBTC','STETH'}
COOLDOWN = 300
last_alert = {}

def get_active_coins(limit=12):
    try:
        data = proxy_mgr.fetch_json(BINANCE + '/api/v3/ticker/24hr', 10)
        if not data:
            return []
        filtered = []
        for d in data:
            sym = d.get('symbol', '')
            if not sym.endswith('USDT'):
                continue
            name = sym.replace('USDT', '')
            if name in SKIP:
                continue
            try:
                chg = abs(float(d.get('priceChangePercent', 0)))
                vol = float(d.get('quoteVolume', 0))
                price = float(d.get('lastPrice', 0))
            except:
                continue
            if vol < 100000 or price < 0.0001:
                continue
            filtered.append((sym, chg, vol, price))
        filtered.sort(key=lambda x: x[1], reverse=True)
        return filtered[:limit]
    except:
        return []

def flash_check(sym):
    reasons = []
    score = 0
    direction = None
    k1m = fetch_klines(sym, '1m', 10)
    if len(k1m) >= 6:
        cv1 = calc_cvd(k1m, 4)
        if cv1 > 35:
            score += 15; reasons.append('1mCVD_buy_' + str(int(cv1)) + '%')
            direction = 'long'
        elif cv1 < -35:
            score -= 15; reasons.append('1mCVD_sell_' + str(int(cv1)) + '%')
            direction = 'short'
        elif cv1 > 20:
            score += 8; reasons.append('1mCVD_buy_' + str(int(cv1)) + '%')
            direction = 'long'
        elif cv1 < -20:
            score -= 8; reasons.append('1mCVD_sell_' + str(int(cv1)) + '%')
            direction = 'short'
    ob = fetch_orderbook_imbalance(sym)
    if ob:
        imb = ob.get('imbalance', 0)
        if imb > 20:
            score += 10; reasons.append('orderbook_buy_' + str(imb) + '%')
            direction = direction or 'long'
        elif imb < -20:
            score -= 10; reasons.append('orderbook_sell_' + str(imb) + '%')
            direction = direction or 'short'
    k5 = fetch_klines(sym, '5m', 12)
    if len(k5) >= 8:
        v5 = [k['v'] for k in k5]
        avg_v = sum(v5[:-1]) / max(len(v5)-1, 1)
        if avg_v > 0:
            vr = v5[-1] / avg_v
            if vr > 3.5:
                bull = k5[-1]['c'] > k5[-1]['o']
                score += (10 if bull else -10)
                reasons.append('5m_vol_' + str(round(vr,1)) + 'x')
    return direction, score, reasons

def scan():
    coins = get_active_coins(10)
    if not coins:
        return
    for sym, chg, vol, price in coins:
        try:
            direction, score, reasons = flash_check(sym)
            if direction is None or abs(score) < 15:
                continue
            ck = sym + '_' + direction
            if ck in last_alert and time.time() - last_alert[ck] < COOLDOWN:
                continue
            now = datetime.now(BJT).strftime('%H:%M:%S')
            name = sym.replace('USDT', '')
            emoji = 'LONG' if direction == 'long' else 'SHORT'
            dir_cn = 'L' if direction == 'long' else 'S'
            lines = [emoji + ' ' + name + ' alert ' + now + ' | $' + str(price) + ' | ' + dir_cn + ' | 24h:' + str(round(chg,1)) + '%']
            for r in reasons:
                lines.append('  ' + r)
            feishu_send(chr(10).join(lines))
            last_alert[ck] = time.time()
        except:
            pass

if __name__ == '__main__':
    feishu_send('Sentinel online | 10s scan | top10 active coins')
    while True:
        try:
            scan()
        except Exception as e:
            print('err:', e)
        time.sleep(10)
