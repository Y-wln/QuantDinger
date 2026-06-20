#!/usr/bin/env python3
'''Diagnose: entry timing vs exit quality'''
import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import proxy_mgr, BINANCE, fetch_klines, ema, rsi, calc_cvd, bollinger_bands

def calc_score(klines_1h, idx):
    c = [k['c'] for k in klines_1h[:idx+1]]
    if len(c) < 50: return None
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

def diagnose_coin(sym, months=6, tp_pct=3, sl_pct=2, max_bars=24):
    bn = sym.replace('USDT','')
    k = fetch_klines(sym, '1h', 744 * months)
    if not k or len(k) < 200: return None
    trades = []
    in_trade = None
    for i in range(50, len(k) - max_bars):
        r = calc_score(k, i)
        if not r: continue
        if in_trade is None and r['signal'] != 'wait':
            # Check price movement in 3 bars BEFORE entry
            pre_move = 0
            if i >= 3:
                if r['signal'] == 'long':
                    pre_move = (k[i]['c'] - k[i-3]['c']) / k[i-3]['c'] * 100
                else:
                    pre_move = (k[i-3]['c'] - k[i]['c']) / k[i-3]['c'] * 100
            in_trade = {'entry_idx': i, 'entry_price': r['price'], 'direction': r['signal'],
                        'score': r['score'], 'pre_move': round(pre_move, 2)}
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
                best_pnl = 0; worst_pnl = 0; first_hit_tp_bar = 999; first_hit_sl_bar = 999
                for j in range(p['entry_idx']+1, i+1):
                    px = k[j]['c']
                    if p['direction'] == 'long':
                        pnl = (px - p['entry_price']) / p['entry_price'] * 100
                    else:
                        pnl = (p['entry_price'] - px) / p['entry_price'] * 100
                    if pnl > best_pnl: best_pnl = pnl
                    if pnl < worst_pnl: worst_pnl = pnl
                    if pnl >= tp_pct and first_hit_tp_bar == 999: first_hit_tp_bar = j - p['entry_idx']
                    if pnl <= -sl_pct and first_hit_sl_bar == 999: first_hit_sl_bar = j - p['entry_idx']
                # Max adverse excursion timing
                mae_bar = 0
                for j in range(p['entry_idx']+1, i+1):
                    px = k[j]['c']
                    if p['direction'] == 'long':
                        pnl = (px - p['entry_price']) / p['entry_price'] * 100
                    else:
                        pnl = (p['entry_price'] - px) / p['entry_price'] * 100
                    if pnl <= worst_pnl + 0.01: mae_bar = j - p['entry_idx']; break
                p['result'] = 'win' if hit_tp else ('loss' if hit_sl else 'timeout')
                p['pnl'] = round(pnl_pct, 2)
                p['bars_held'] = bars_held
                p['best_pnl'] = round(best_pnl, 2)
                p['worst_pnl'] = round(worst_pnl, 2)
                p['mae_bar'] = mae_bar
                p['first_tp_bar'] = first_hit_tp_bar if first_hit_tp_bar < 999 else -1
                p['first_sl_bar'] = first_hit_sl_bar if first_hit_sl_bar < 999 else -1
                p['drew_first'] = 'hit_sl_first' if (first_hit_sl_bar < first_hit_tp_bar) else ('hit_tp_first' if first_hit_tp_bar < 999 else 'never_hit_either')
                trades.append(p)
                in_trade = None
    if not trades: return None
    wins = [t for t in trades if t['result'] == 'win']
    losses = [t for t in trades if t['result'] == 'loss']
    # Late entry = pre_move already >1.5% in signal direction
    late = [t for t in trades if t['pre_move'] > 1.5]
    early = [t for t in trades if t['pre_move'] < 0.5]
    # Hit SL before TP (false signal)
    sl_first = [t for t in trades if t['drew_first'] == 'hit_sl_first']
    # Trades where best_pnl > 3% but exited as loss/timeout
    missed = [t for t in trades if t['best_pnl'] >= 3 and t['result'] != 'win']
    return {
        'sym': bn, 'trades': len(trades), 'wins': len(wins), 'losses': len(losses),
        'late_entries': len(late), 'early_entries': len(early),
        'sl_first': len(sl_first), 'missed_ops': len(missed),
        'avg_pre_move': round(sum(t['pre_move'] for t in trades)/len(trades), 2),
        'avg_mae_bar': round(sum(t['mae_bar'] for t in trades)/len(trades), 1),
        'win_rate': round(len(wins)/len(trades)*100, 1),
        'total_pnl': round(sum(t['pnl'] for t in trades), 2),
        'best_pnl': round(max(t['best_pnl'] for t in trades), 2),
    }

if __name__ == '__main__':
    coins = ['BTCUSDT','ETHUSDT','SOLUSDT','DASHUSDT','INJUSDT','TAOUSDT','CHZUSDT','DOGEUSDT']
    print('Diagnosis: Entry Timing Analysis')
    print('=' * 90)
    print('COIN   Trades  WR%    TotPnL  Late%   PreMove  MAE_bar  SLfirst  Missed  BestPnl')
    print('-' * 90)
    for sym in coins:
        r = diagnose_coin(sym, months=6)
        if r:
            late_pct = round(r['late_entries']/r['trades']*100, 1)
            slf_pct = round(r['sl_first']/r['trades']*100, 1)
            miss_pct = round(r['missed_ops']/r['trades']*100, 1)
            print(r['sym'].ljust(6), str(r['trades']).rjust(5), str(r['win_rate']).rjust(5)+'%',
                  str(r['total_pnl']).rjust(7)+'%', str(late_pct).rjust(5)+'%',
                  str(r['avg_pre_move']).rjust(7)+'%', str(r['avg_mae_bar']).rjust(7)+'h',
                  str(slf_pct).rjust(6)+'%', str(miss_pct).rjust(6)+'%', str(r['best_pnl']).rjust(7)+'%')
    print()
    print('Late = pre_move>1.5% (entering after move started)')
    print('SLfirst = hit stop-loss before take-profit')
    print('Missed = best_pnl>3% but exited loss/timeout (good call bad exit)')
