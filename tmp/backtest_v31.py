#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v31 ?????? - 6??"""
import sys, os, json, time
from datetime import datetime, timedelta
sys.path.insert(0, '/home/ubuntu/scripts/agents')

COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'BNBUSDT', 'XRPUSDT']
BINANCE = 'https://api.binance.com'

def fetch_hist_klines(symbol, interval, start_ts, end_ts, limit=1000):
    from urllib.request import Request, build_opener, ProxyHandler
    ph = ProxyHandler({'http':'http://127.0.0.1:7892','https':'http://127.0.0.1:7892'})
    opener = build_opener(ph)
    all_klines = []
    current_start = start_ts
    while current_start < end_ts:
        url = f'{BINANCE}/api/v3/klines?symbol={symbol}&interval={interval}&startTime={current_start}000&limit={limit}'
        try:
            req = Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read())
            if not data:
                break
            all_klines.extend(data)
            last_time = data[-1][0]
            if last_time >= end_ts * 1000:
                break
            current_start = last_time + 1
            time.sleep(0.3)
        except Exception as e:
            print(f'  fetch error: {e}')
            time.sleep(2)
    return [{'t':int(k[0])//1000,'o':float(k[1]),'h':float(k[2]),'l':float(k[3]),'c':float(k[4]),'v':float(k[5])} for k in all_klines]

def run_backtest(symbol):
    print(f'\n{"="*50}')
    print(f'  {symbol} ?????? (v31)')
    print(f'{"="*50}')

    # Time range: Jan 1 - Jun 10 2026
    start_ts = int(datetime(2026, 1, 1).timestamp())
    end_ts = int(datetime(2026, 6, 10).timestamp())

    # Fetch 4h klines for trend + 1h for signal + 5m for entry
    print('  ??4h K?...')
    k4 = fetch_hist_klines(symbol, '4h', start_ts, end_ts, 500)
    print(f'  4h: {len(k4)}?')
    print('  ??1h K?...')
    k1 = fetch_hist_klines(symbol, '1h', start_ts, end_ts, 500)
    print(f'  1h: {len(k1)}?')
    print('  ??5m K?...')
    k5 = fetch_hist_klines(symbol, '5m', start_ts, end_ts, 500)
    print(f'  5m: {len(k5)}?')

    if len(k4) < 50 or len(k1) < 50 or len(k5) < 50:
        print(f'  ???????')
        return None

    from hermes_core import ema, rsi, macd, supertrend, calc_cvd, detect_structure, bollinger_bands, atr

    trades = []
    position = None  # {'direction','entry_price','entry_time','sl','tp'}
    equity = 1000  # base capital
    max_equity = 1000
    max_dd = 0

    # Walk through 1h candles for signals
    for i in range(100, len(k1)):
        # Get 4h context
        current_time = k1[i]['t']
        k4_slice = [k for k in k4 if k['t'] <= current_time]
        if len(k4_slice) < 50:
            continue
        k4_slice = k4_slice[-100:]

        # Get 5m context for entry
        k5_slice = [k for k in k5 if current_time - 7200 <= k['t'] <= current_time]
        if len(k5_slice) < 20:
            continue

        # Check SL/TP if in position
        if position:
            current_price = k1[i]['c']
            if position['direction'] == 'long':
                if current_price <= position['sl']:
                    pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
                    trades.append({'type':'SL','pnl':pnl,'entry':position['entry_price'],'exit':current_price,'time':current_time})
                    equity *= (1 + pnl/100)
                    position = None
                elif current_price >= position['tp']:
                    pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
                    trades.append({'type':'TP','pnl':pnl,'entry':position['entry_price'],'exit':current_price,'time':current_time})
                    equity *= (1 + pnl/100)
                    position = None
            else:  # short
                if current_price >= position['sl']:
                    pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
                    trades.append({'type':'SL','pnl':pnl,'entry':position['entry_price'],'exit':current_price,'time':current_time})
                    equity *= (1 + pnl/100)
                    position = None
                elif current_price <= position['tp']:
                    pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
                    trades.append({'type':'TP','pnl':pnl,'entry':position['entry_price'],'exit':current_price,'time':current_time})
                    equity *= (1 + pnl/100)
                    position = None

        max_equity = max(max_equity, equity)
        dd = (max_equity - equity) / max_equity * 100
        max_dd = max(max_dd, dd)

        if position:
            continue

        # ====== Calculate scores (simplified v31) ======
        score = 0
        c4 = [k['c'] for k in k4_slice]
        c1_slice = [k['c'] for k in k1[max(0,i-99):i+1]]
        if len(c1_slice) < 50:
            continue

        # Structure
        struct4, _ = detect_structure(k4_slice)
        struct1, _ = detect_structure(k1[max(0,i-99):i+1])
        if struct4 == 'up': score += 6
        elif struct4 == 'down': score -= 6
        if struct1 == 'up': score += 4 if score > 0 else 2
        elif struct1 == 'down': score -= 4 if score < 0 else 2

        # SuperTrend
        st4, _ = supertrend(k4_slice)
        if st4 == 'long': score += 6
        else: score -= 6

        # RSI
        rsi4 = rsi(c4)
        if rsi4 < 30: score += 8
        elif rsi4 > 70: score -= 8
        elif rsi4 > 50: score += 4
        else: score -= 4

        # MACD
        md, mdea, mh = macd(c4)
        if md > mdea and mh > 0: score += 5
        elif md < mdea and mh < 0: score -= 5

        # CVD
        cv4 = calc_cvd(k4_slice, 6)
        cv1h = calc_cvd(k1[max(0,i-99):i+1], 6)
        if cv4 > 20: score += 6
        elif cv4 < -20: score -= 6
        if cv1h > 20: score += 8
        elif cv1h < -20: score -= 8

        # 5m CVD
        cv5 = calc_cvd(k5_slice[-6:], 6)
        if cv5 > 15: score += 10
        elif cv5 < -15: score -= 10
        elif cv5 > 8: score += 5
        elif cv5 < -8: score -= 5

        # 5m volume breakout
        v5 = [k['v'] for k in k5_slice]
        if len(v5) >= 12:
            avg_v = sum(v5[-11:-1])/10 if len(v5)>=11 else 1
            if avg_v > 0 and v5[-1] / avg_v > 2.0:
                if k5_slice[-1]['c'] > k5_slice[-1]['o']:
                    score += 8
                else:
                    score -= 8

        # Bollinger squeeze
        bb = bollinger_bands(c4)
        if bb and bb['squeeze']:
            score += 5 if score > 0 else -5

        # Signal decision
        if score >= 18:
            direction = 'long'
        elif score <= -18:
            direction = 'short'
        else:
            continue

        # Open position
        entry_price = k1[i]['c']
        a = atr(k4_slice)
        sl_pct = max(0.02, min(0.05, a/entry_price * 2))
        tp_pct = max(0.03, min(0.08, a/entry_price * 3))

        if direction == 'long':
            sl = entry_price * (1 - sl_pct)
            tp = entry_price * (1 + tp_pct)
        else:
            sl = entry_price * (1 + sl_pct)
            tp = entry_price * (1 - tp_pct)

        position = {
            'direction': direction,
            'entry_price': entry_price,
            'entry_time': current_time,
            'sl': sl,
            'tp': tp
        }

    # Close any remaining position
    if position:
        last_price = k1[-1]['c']
        if position['direction'] == 'long':
            pnl = (last_price - position['entry_price']) / position['entry_price'] * 100
        else:
            pnl = (position['entry_price'] - last_price) / position['entry_price'] * 100
        trades.append({'type':'CLOSE','pnl':pnl,'entry':position['entry_price'],'exit':last_price,'time':k1[-1]['t']})
        equity *= (1 + pnl/100)

    wins = sum(1 for t in trades if t['pnl'] > 0)
    total_pnl = (equity - 1000) / 1000 * 100
    wr = wins / len(trades) * 100 if trades else 0
    avg_pnl = sum(t['pnl'] for t in trades) / len(trades) if trades else 0
    avg_tp = sum(t['pnl'] for t in trades if t['pnl']>0) / max(1, sum(1 for t in trades if t['pnl']>0))
    avg_sl = sum(t['pnl'] for t in trades if t['pnl']<0) / max(1, sum(1 for t in trades if t['pnl']<0))

    print(f'  ??: {len(trades)}? | ??: {wr:.1f}% | ?PnL: {total_pnl:+.1f}%')
    print(f'  ??: {avg_tp:+.2f}% | ??: {avg_sl:+.2f}% | ????: {max_dd:.1f}%')

    return {'symbol':symbol,'trades':len(trades),'wr':round(wr,1),'total_pnl':round(total_pnl,1),
            'avg_pnl':round(avg_pnl,2),'avg_tp':round(avg_tp,2),'avg_sl':round(avg_sl,2),'max_dd':round(max_dd,1)}

# Run
results = []
for sym in COINS:
    r = run_backtest(sym)
    if r:
        results.append(r)

print(f'\n{"="*60}')
print(f'  ??')
print(f'{"="*60}')
print(f'  {"??":<8} {"??":>5} {"??":>7} {"???":>8} {"??":>8} {"??":>8} {"??":>6}')
print(f'  {"-"*56}')
for r in results:
    print(f'  {r["symbol"].replace("USDT",""):<8} {r["trades"]:>5} {r["wr"]:>6.1f}% {r["total_pnl"]:>+7.1f}% {r["avg_tp"]:>+7.2f}% {r["avg_sl"]:>+7.2f}% {r["max_dd"]:>5.1f}%')

if results:
    total_trades = sum(r['trades'] for r in results)
    avg_wr = sum(r['wr']*r['trades'] for r in results)/total_trades if total_trades else 0
    total_pnl = sum(r['total_pnl'] for r in results) / len(results)
    print(f'  {"-"*56}')
    print(f'  {"??":<8} {total_trades:>5} {avg_wr:>6.1f}% {total_pnl:>+7.1f}%')
