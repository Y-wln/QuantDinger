# -*- coding: utf-8 -*-
"""Hermes v30.20 ?????? (???)"""
import sys, os, json, time
from datetime import datetime, timedelta
sys.path.insert(0, '/home/ubuntu/scripts/agents')

from hermes_core import (fetch_klines, fetch_fear_greed, fetch_price,
    ema, rsi, atr, macd, supertrend, calc_cvd, detect_structure,
    bollinger_bands, detect_launch, cvd_snap_detect)
from agent_technical import TechnicalAgent

COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
    'DOGEUSDT', 'LINKUSDT', 'AVAXUSDT', 'DOTUSDT', 'LTCUSDT', 'INJUSDT',
    'APTUSDT', 'FETUSDT', 'AAVEUSDT']

def run_backtest(symbol, days=180):
    print(f"\n{'='*60}")
    print(f"  {symbol} ??({days}?)???? v30.20")
    print(f"{'='*60}")

    # Fetch 6 months of 4h data
    k4 = fetch_klines(symbol, '4h', 1100)
    k1 = fetch_klines(symbol, '1h', 300)
    if len(k4) < 200 or len(k1) < 200:
        print(f"  ????: 4h={len(k4)}, 1h={len(k1)}")
        return None

    agent = TechnicalAgent()
    trades = []
    position = None
    entry_price = 0
    entry_time = None

    # Get FnG history if possible, else use fixed value
    fng = 50

    # Slide through 4h candles (each = 1 analysis point)
    for i in range(100, len(k4) - 1):
        # Build rolling windows
        k4_window = k4[max(0,i-100):i+1]
        k1_start = max(0, len(k1) - (len(k4)-i)*4 - 50)
        k1_window = k1[max(0, k1_start):min(len(k1), k1_start+200)]
        if len(k4_window) < 50 or len(k1_window) < 50:
            continue

        price = k4[i]['c']
        result = agent.analyze(k4_window, k1_window, [], [], symbol, fng=fng)

        if position is None:
            if result['signal'] in ('long', 'short'):
                direction = result['signal']
                abs_score = abs(result['score'])
                # Higher threshold for backtest
                if abs_score >= 30:
                    position = direction
                    entry_price = price
                    entry_time = i
        else:
            # Check exit conditions
            pp = (price - entry_price) / entry_price * 100
            if position == 'short':
                pp = -pp

            # Trail stop: 3% after entry
            sl_hit = pp <= -3.0
            tp_hit = pp >= 5.0

            # Also exit on signal reversal with sufficient strength
            signal_reverse = (position == 'long' and result['signal'] == 'short' and abs(result['score']) >= 25) or \
                           (position == 'short' and result['signal'] == 'long' and abs(result['score']) >= 25)

            # Max hold 48 bars (8 days of 4h)
            max_hold = (i - entry_time) > 48 if entry_time else False

            if sl_hit or tp_hit or signal_reverse or max_hold:
                exit_reason = '??' if tp_hit else ('??' if sl_hit else ('??' if signal_reverse else '??'))
                trades.append({
                    'symbol': symbol,
                    'direction': position,
                    'entry': round(entry_price, 4),
                    'exit': round(price, 4),
                    'pnl_pct': round(pp, 2),
                    'reason': exit_reason,
                    'bars_held': i - entry_time if entry_time else 0,
                    'entry_score': abs_score
                })
                position = None
                entry_price = 0
                entry_time = None

    # Stats
    if not trades:
        print(f"  ?????")
        return {'symbol': symbol, 'trades': 0, 'wr': 0, 'total_pnl': 0, 'avg_pnl': 0}

    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    wr = len(wins) / len(trades) * 100 if trades else 0
    total_pnl = sum(t['pnl_pct'] for t in trades)
    avg_pnl = total_pnl / len(trades) if trades else 0

    long_trades = [t for t in trades if t['direction'] == 'long']
    short_trades = [t for t in trades if t['direction'] == 'short']

    print(f"  ??: {len(trades)}? | ??: {wr:.0f}% | ??: {total_pnl:+.1f}% | ??: {avg_pnl:+.1f}%")
    print(f"  ??: {len(long_trades)}? ({'+' if sum(t['pnl_pct'] for t in long_trades)>0 else ''}{sum(t['pnl_pct'] for t in long_trades):.1f}%)")
    print(f"  ??: {len(short_trades)}? ({'+' if sum(t['pnl_pct'] for t in short_trades)>0 else ''}{sum(t['pnl_pct'] for t in short_trades):.1f}%)")

    # Show first and last 3
    for t in trades[:3]:
        emoji = '\U0001F7E2' if t['pnl_pct'] > 0 else '\U0001F534'
        direction_cn = '?' if t['direction'] == 'long' else '?'
        print(f"  {emoji} {direction_cn} {t['entry']}->{t['exit']}: {t['pnl_pct']:+.1f}% ({t['reason']}, {t['bars_held']}?)")

    return {
        'symbol': symbol,
        'trades': len(trades),
        'wr': round(wr, 1),
        'total_pnl': round(total_pnl, 1),
        'avg_pnl': round(avg_pnl, 2),
        'longs': len(long_trades),
        'shorts': len(short_trades),
        'win_count': len(wins),
        'loss_count': len(losses)
    }


if __name__ == '__main__':
    print('Hermes v30.20 ??????')
    print(f'????: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'??: {len(COINS)}?')

    results = []
    for sym in COINS:
        try:
            r = run_backtest(sym)
            if r:
                results.append(r)
            time.sleep(1)
        except Exception as e:
            print(f'  {sym} ????: {e}')

    print(f'\n{"="*60}')
    print(f'  ???? (v30.20)')
    print(f'{"="*60}')

    results.sort(key=lambda x: x.get('total_pnl', 0), reverse=True)
    for r in results:
        emoji = '\U0001F7E2' if r.get('total_pnl', 0) > 0 else '\U0001F534'
        print(f"  {emoji} {r['symbol']}: {r['trades']}? {r['wr']}%?? {r['total_pnl']:+5.1f}%")

    # Save
    with open('/home/ubuntu/scripts/backtest_v30_20.json', 'w') as f:
        json.dump({'version': 'v30.20', 'time': datetime.now().isoformat(), 'results': results}, f, indent=2)
    print(f'\n?????: ~/scripts/backtest_v30_20.json')
