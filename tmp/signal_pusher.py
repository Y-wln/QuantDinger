#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""?????? ? ???1m/5m???????????"""
import sys, os, time, json, threading
from datetime import datetime, timezone, timedelta
BJT = timezone(timedelta(hours=8))

sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import (fetch_klines, fetch_price, fetch_fear_greed, calc_cvd,
    fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure,
    fetch_taker_volume, fetch_funding_rate,
    feishu_send, BINANCE, BINANCE_F)

COINS = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT',
    'DOGEUSDT','LINKUSDT','AVAXUSDT','DOTUSDT','LTCUSDT','INJUSDT']

SCAN_INTERVAL = 15  # 15????
COOLDOWN = 300       # ?????5????
MIN_SCORE = 12       # ???????(????)

last_alert = {}

def quick_launch_score(sym):
    """???????? 20??"""
    score = 0
    reasons = []

    # 5m K?
    k5 = fetch_klines(sym, '5m', 12)
    if len(k5) < 8:
        return 0, []

    # 5m CVD
    cv5 = calc_cvd(k5, 4)
    if cv5 > 25:
        score += 8; reasons.append(f'5mCVD??{cv5:.0f}%')
    elif cv5 < -25:
        score -= 8; reasons.append(f'5mCVD??{cv5:.0f}%')
    elif cv5 > 12:
        score += 4; reasons.append(f'5mCVD??{cv5:.0f}%')
    elif cv5 < -12:
        score -= 4; reasons.append(f'5mCVD??{cv5:.0f}%')

    # 5m ??
    v5 = [k['v'] for k in k5]
    avg_v = sum(v5[:-1]) / max(len(v5)-1, 1)
    if avg_v > 0:
        vr = v5[-1] / avg_v
        if vr > 2.5:
            score += (6 if cv5 > 0 else -6)
            reasons.append(f'5m??{vr:.1f}x')
        elif vr > 1.5:
            score += (3 if cv5 > 0 else -3)
            reasons.append(f'5m??{vr:.1f}x')

    # ????
    c5 = [k['c'] for k in k5]
    mom = (c5[-1] - c5[0]) / c5[0] * 100
    if abs(mom) > 1.5:
        score += (6 if mom > 0 else -6)
        reasons.append(f'5m??{mom:+.1f}%')

    # 1m CVD (??)
    k1m = fetch_klines(sym, '1m', 10)
    if len(k1m) >= 6:
        cv1 = calc_cvd(k1m, 4)
        if abs(cv1) > 30:
            score += (6 if cv1 > 0 else -6)
            reasons.append(f'1mCVD{cv1:.0f}%')

    return score, reasons

def push_signal(sym, price, score, reasons):
    now = datetime.now(BJT).strftime('%H:%M:%S')
    d = '??' if score > 0 else '??'
    emoji = '\U0001f7e2' if score > 0 else '\U0001f534'

    msg = f'{emoji} \U0001f525 {sym.replace("USDT","")} ????\n'
    msg += f'\u23f0 {now} | ${price} | {d} | ??:{abs(score)}\n'
    msg += f'{"-"*20}\n'
    for r in reasons:
        msg += f'  \u27a4 {r}\n'
    msg += f'\U0001f4a1 ????????????????'

    feishu_send(msg)
    print(f'[{now}] PUSH {sym} {d} score={score}')

def scan():
    for sym in COINS:
        try:
            score, reasons = quick_launch_score(sym)
            if abs(score) < MIN_SCORE:
                continue

            d = 'long' if score > 0 else 'short'
            ck = f'{sym}_{d}'
            now = time.time()
            if ck in last_alert and now - last_alert[ck] < COOLDOWN:
                continue

            price = fetch_price(sym)
            if price <= 0:
                continue

            push_signal(sym, price, score, reasons)
            last_alert[ck] = now
        except Exception:
            pass

if __name__ == '__main__':
    print(f'[{datetime.now(BJT).strftime("%H:%M:%S")}] ???????? | 12? | {SCAN_INTERVAL}s?? | ??{COOLDOWN}s')
    feishu_send(f'\U0001f514 ????????? | 12???? | {SCAN_INTERVAL}s??')
    while True:
        try:
            scan()
        except Exception as e:
            print(f'??: {e}')
        time.sleep(SCAN_INTERVAL)
