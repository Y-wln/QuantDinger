#!/usr/bin/env python3
import sys, json, time
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import proxy_mgr, BINANCE, fetch_klines, ema, rsi, calc_cvd, bollinger_bands

def calc_score(klines_1h, idx):
    c = [k['c'] for k in klines_1h[:idx+1]]
    if len(c) < 50:
        return None
    rs_arr = rsi(c)
    rs = float(rs_arr[-1]) if isinstance(rs_arr, list) and len(rs_arr) > 0 else 50
    cv = calc_cvd(klines_1h[:idx+1], 6)
    e20_arr = ema(c, 20)
    e50_arr = ema(c, 50)
    e20 = float(e20_arr[-1]) if isinstance(e20_arr, list) and len(e20_arr) > 0 else c[-1]
    e50 = float(e50_arr[-1]) if isinstance(e50_arr, list) and len(e50_arr) > 0 else c[-1]
    price = c[-1]
    trend_1h = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')
    cv_prev = calc_cvd(klines_1h[max(0,idx-11):idx+1], min(6, idx+1)) if idx >= 6 else cv
    cv_delta = cv - cv_prev
    bb = bollinger_bands(c, 20, 2)
    bb_squeeze = bb.get('squeeze', False) if bb else False
    score = 0
    if cv > 20: score += 10
    elif cv < -20: score -= 10
    elif cv > 10: score += 5
    elif cv < -10: score -= 5
    if cv > 10 and abs(cv_delta) > 5: score += 10
    elif cv < -10 and abs(cv_delta) > 5: score -= 10
    if rs < 25: score += 10
    elif rs < 35: score += 5
    elif rs > 75: score -= 10
    elif rs > 65: score -= 5
    if bb_squeeze:
        if cv > 5: score += 8
        elif cv < -5: score -= 8
    if trend_1h == 'up': score += 8
    elif trend_1h == 'down': score -= 8
    sig = 'long' if score >= 10 else ('short' if score <= -10 else 'wait')
    return {'signal':sig, 'score':score, 'price':price, 'rsi':rs, 'cvd':cv, 'cv_delta':cv_delta, 'trend':trend_1h}

def backtest_coin(sym, months=6, tp_pct=3, sl_pct=2, min_bars=3, max_bars=24):
    bn = sym.replace('USDT','')
    print('  Fetching ' + bn + ' ' + str(months) + 'mo data...', end=' ', flush=True)
    k = fetch_klines(sym, '1h', 744 * months)
    if not k or len(k) < 200:
        print('FAIL (got ' + str(len(k) if k else 0) + ' bars)')
        return None
    print(str(len(k)) + ' bars OK')
    trades = []
    in_trade = None
    for i in range(50, len(k) - max_bars):
        r = calc_score(k, i)
        if not r: continue
        if in_trade is None and r['signal'] != 'wait':
            in_trade = {'entry_idx': i, 'entry_price': r['price'], 'direction': r['signal'],
                        'score': r['score'], 'entry_time': str(i)}
        elif in_trade is not None:
            p = in_trade
            bars_held = i - p['entry_idx']
            current_price = k[i]['c']
            if p['direction'] == 'long':
                pnl_pct = (current_price - p['entry_price']) / p['entry_price'] * 100
            else:
                pnl_pct = (p['entry_price'] - current_price) / p['entry_price'] * 100
            hit_tp = pnl_pct >= tp_pct
            hit_sl = pnl_pct <= -sl_pct
            timeout = bars_held >= max_bars
            if hit_tp or hit_sl or timeout:
                best_pnl = 0
                worst_pnl = 0
                for j in range(p['entry_idx']+min_bars, i+1):
                    px = k[j]['c']
                    if p['direction'] == 'long':
                        pnl = (px - p['entry_price']) / p['entry_price'] * 100
                    else:
                        pnl = (p['entry_price'] - px) / p['entry_price'] * 100
                    if pnl > best_pnl: best_pnl = pnl
                    if pnl < worst_pnl: worst_pnl = pnl
                p['result'] = 'win' if hit_tp else ('loss' if hit_sl else 'timeout')
                p['exit_idx'] = i
                p['exit_price'] = current_price
                p['pnl'] = round(pnl_pct, 2)
                p['bars_held'] = bars_held
                p['best_pnl'] = round(best_pnl, 2)
                p['worst_pnl'] = round(worst_pnl, 2)
                trades.append(p)
                in_trade = None
    if not trades:
        return {'sym': bn, 'trades': 0, 'win_rate': 0, 'avg_bars': 0, 'avg_pnl': 0}
    wins = [t for t in trades if t['result'] == 'win']
    losses = [t for t in trades if t['result'] == 'loss']
    timeouts = [t for t in trades if t['result'] == 'timeout']
    return {
        'sym': bn, 'trades': len(trades), 'wins': len(wins), 'losses': len(losses), 'timeouts': len(timeouts),
        'win_rate': round(len(wins)/len(trades)*100, 1) if trades else 0,
        'avg_bars': round(sum(t['bars_held'] for t in trades)/len(trades), 1) if trades else 0,
        'avg_pnl': round(sum(t['pnl'] for t in trades)/len(trades), 2) if trades else 0,
        'best_pnl': round(max(t['best_pnl'] for t in trades), 2) if trades else 0,
        'worst_pnl': round(min(t['worst_pnl'] for t in trades), 2) if trades else 0,
        'total_pnl': round(sum(t['pnl'] for t in trades), 2),
    }

if __name__ == '__main__':
    coins = ['BTCUSDT','ETHUSDT','SOLUSDT','DASHUSDT','INJUSDT','TAOUSDT','CHZUSDT','DOGEUSDT']
    print('=' * 60)
    print('Yaobi v9 Backtest | 6mo 1h | TP=3% SL=2% | Min=3h Max=24h')
    print('=' * 60)
    results = []
    for sym in coins:
        r = backtest_coin(sym, months=6)
        if r:
            results.append(r)
            line = '  ' + r['sym'].ljust(6) + ' | ' + str(r['trades']).rjust(3) + ' trades | WR:' + str(r['win_rate']).rjust(5) + '% | hold:' + str(r['avg_bars']).rjust(4) + 'h | avgPnL:' + ('+' if r['avg_pnl']>=0 else '') + str(r['avg_pnl']) + '% | total:' + ('+' if r['total_pnl']>=0 else '') + str(r['total_pnl']) + '% | best:' + str(r['best_pnl']) + '% | worst:' + str(r['worst_pnl']) + '%'
            print(line)
    print()
    print('=' * 60)
    total_trades = sum(r['trades'] for r in results)
    total_wins = sum(r['wins'] for r in results)
    total_pnl = sum(r['total_pnl'] for r in results)
    wr = round(total_wins/total_trades*100, 1) if total_trades else 0
    print('Total: ' + str(total_trades) + ' trades, ' + str(total_wins) + ' wins, WR=' + str(wr) + '%, SumPnL=' + ('+' if total_pnl>=0 else '') + str(total_pnl) + '%')
