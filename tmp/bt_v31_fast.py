#!/usr/bin/env python3
"""v31 3???? - ?4h+1h??"""
import sys, json, time
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import ema, rsi, macd, supertrend, calc_cvd, detect_structure, bollinger_bands, atr, fetch_klines

COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'BNBUSDT', 'XRPUSDT']

def run_backtest(symbol):
    print(f'\n{"="*50}')
    print(f'  {symbol}')
    k4 = fetch_klines(symbol, '4h', 500)
    k1 = fetch_klines(symbol, '1h', 500)
    if len(k4) < 100 or len(k1) < 100:
        print(f'  data insufficient: 4h={len(k4)} 1h={len(k1)}')
        return None
    print(f'  4h:{len(k4)} 1h:{len(k1)} | {k4[0]["t"]} ~ {k4[-1]["t"]}')

    trades = []
    position = None
    equity = 1000; max_eq = 1000; max_dd = 0
    scores_seen = []

    for i in range(100, len(k1)):
        ct = k1[i]['t']
        # Find 4h context
        k4_slice = [k for k in k4 if k['t'] <= ct][-100:]
        k1_slice = k1[max(0,i-99):i+1]
        if len(k4_slice) < 50 or len(k1_slice) < 30:
            continue

        if position:
            price = k1[i]['c']
            d = position['direction']
            if d == 'long':
                if price <= position['sl']:
                    pnl = (price-position['entry'])/position['entry']*100
                    trades.append({'pnl':pnl,'type':'SL'})
                    equity *= (1+pnl/100); position = None
                elif price >= position['tp']:
                    pnl = (price-position['entry'])/position['entry']*100
                    trades.append({'pnl':pnl,'type':'TP'})
                    equity *= (1+pnl/100); position = None
            else:
                if price >= position['sl']:
                    pnl = (position['entry']-price)/position['entry']*100
                    trades.append({'pnl':pnl,'type':'SL'})
                    equity *= (1+pnl/100); position = None
                elif price <= position['tp']:
                    pnl = (position['entry']-price)/position['entry']*100
                    trades.append({'pnl':pnl,'type':'TP'})
                    equity *= (1+pnl/100); position = None
            max_eq = max(max_eq, equity)
            max_dd = max(max_dd, (max_eq-equity)/max_eq*100)
            continue

        # Scoring (v31 weights)
        score = 0
        c4 = [k['c'] for k in k4_slice]
        c1 = [k['c'] for k in k1_slice]

        struct4, _ = detect_structure(k4_slice)
        struct1, _ = detect_structure(k1_slice)
        if struct4 == 'up': score += 6
        elif struct4 == 'down': score -= 6
        if struct1 == 'up': score += (4 if score>0 else 2)
        elif struct1 == 'down': score -= (4 if score<0 else 2)

        st4, _ = supertrend(k4_slice)
        if st4 == 'long': score += 6
        else: score -= 6

        rs = rsi(c4)
        if rs < 30: score += 8
        elif rs > 70: score -= 8
        elif rs > 50: score += 4
        else: score -= 4

        md, mdea, mh = macd(c4)
        if md > mdea and mh > 0: score += 5
        elif md < mdea and mh < 0: score -= 5

        cv4 = calc_cvd(k4_slice, 6)
        cv1 = calc_cvd(k1_slice, 6)
        if cv4 > 20: score += 6
        elif cv4 < -20: score -= 6
        if cv1 > 20: score += 8
        elif cv1 < -20: score -= 8

        bb = bollinger_bands(c4)
        if bb and bb['squeeze']:
            score += (5 if score > 0 else -5)

        scores_seen.append(score)

        if score >= 18:
            direction = 'long'
        elif score <= -18:
            direction = 'short'
        else:
            continue

        price = k1[i]['c']
        a = atr(k4_slice)
        sl_pct = max(0.02, min(0.05, a/price*2))
        tp_pct = max(0.03, min(0.08, a/price*3))
        if direction == 'long':
            sl = price*(1-sl_pct); tp = price*(1+tp_pct)
        else:
            sl = price*(1+sl_pct); tp = price*(1-tp_pct)
        position = {'direction':direction,'entry':price,'sl':sl,'tp':tp}

    if position:
        lp = k1[-1]['c']
        pnl = (lp-position['entry'])/position['entry']*100 if position['direction']=='long' else (position['entry']-lp)/position['entry']*100
        trades.append({'pnl':pnl,'type':'CLOSE'})
        equity *= (1+pnl/100)

    wins = sum(1 for t in trades if t['pnl']>0)
    wr = wins/len(trades)*100 if trades else 0
    tp = (equity-1000)/1000*100
    avg_p = sum(t['pnl'] for t in trades)/len(trades) if trades else 0
    avg_tp = sum(t['pnl'] for t in trades if t['pnl']>0)/max(1,sum(1 for t in trades if t['pnl']>0))
    avg_sl = sum(t['pnl'] for t in trades if t['pnl']<0)/max(1,sum(1 for t in trades if t['pnl']<0))

    print(f'  ??:{len(trades)} ??:{wr:.1f}% PnL:{tp:+.1f}% ??:{avg_tp:+.2f}% ??:{avg_sl:+.2f}% ??:{max_dd:.1f}%')
    print(f'  ????: {min(scores_seen) if scores_seen else 0} ~ {max(scores_seen) if scores_seen else 0}')
    return {'symbol':symbol.replace('USDT',''),'trades':len(trades),'wr':round(wr,1),
            'pnl':round(tp,1),'avg_tp':round(avg_tp,2),'avg_sl':round(avg_sl,2),'dd':round(max_dd,1)}

results = []
for sym in COINS:
    r = run_backtest(sym)
    if r: results.append(r)
    time.sleep(1)

print(f'\n{"="*60}')
print(f'  {"??":<8} {"??":>5} {"??":>7} {"???":>8} {"??":>8} {"??":>8} {"??":>6}')
print(f'  {"-"*56}')
for r in results:
    print(f'  {r["symbol"]:<8} {r["trades"]:>5} {r["wr"]:>6.1f}% {r["pnl"]:>+7.1f}% {r["avg_tp"]:>+7.2f}% {r["avg_sl"]:>+7.2f}% {r["dd"]:>5.1f}%')
if results:
    total_t = sum(r['trades'] for r in results)
    avg_wr = sum(r['wr']*r['trades'] for r in results)/total_t if total_t else 0
    avg_pnl = sum(r['pnl'] for r in results)/len(results)
    print(f'  {"-"*56}')
    print(f'  {"??":<8} {total_t:>5} {avg_wr:>6.1f}% {avg_pnl:>+7.1f}%')
