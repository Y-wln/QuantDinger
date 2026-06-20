#!/usr/bin/env python3
"""sentinel v6 - paper trading with reversal-based exit"""
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
COOLDOWN = 180
MAX_POS = 5

# Paper trading state
positions = {}   # sym -> {direction, entry_price, peak_price, pnl, time}
total_pnl = 0.0
total_trades = 0
TP_TRAIL = 0.008  # Trail stop: exit when price drops 0.8% from peak (long)
SL_PCT = 0.015    # Hard stop: 1.5% loss

def scan():
    global total_pnl, total_trades
    try:
        data = proxy_mgr.fetch_json(BINANCE_F + '/fapi/v1/ticker/bookTicker', 4)
        if not data:
            return
        now = time.time()

        # Build price map for position monitoring
        price_map = {}
        for t in data:
            sym = t.get('symbol','')
            if not sym.endswith('USDT'): continue
            name = sym.replace('USDT','')
            if name in SKIP: continue
            try:
                bid = float(t.get('bidPrice',0))
                ask = float(t.get('askPrice',0))
                price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
                bid_qty = float(t.get('bidQty',0))
                ask_qty = float(t.get('askQty',0))
                if price <= 0: continue
            except: continue
            price_map[sym] = (price, bid_qty, ask_qty)

        # === Position management (check every scan) ===
        closed_positions = []
        for sym, pos in list(positions.items()):
            if sym not in price_map: continue
            price, _, _ = price_map[sym]
            entry = pos['entry_price']
            peak = pos.get('peak_price', entry)
            direction = pos['direction']

            if direction == 'LONG':
                # Update peak
                if price > peak:
                    pos['peak_price'] = price
                    peak = price
                # Trail stop: exit when drops 0.8% from peak
                trail_stop = peak * (1 - TP_TRAIL)
                hard_stop = entry * (1 - SL_PCT)
                if price <= trail_stop or price <= hard_stop:
                    pnl_pct = (price - entry) / entry * 100
                    total_pnl += pnl_pct
                    total_trades += 1
                    reason = '止盈' if price <= trail_stop and pnl_pct > 0 else '止损'
                    closed_positions.append((sym, direction, entry, price, pnl_pct, reason))
                    del positions[sym]
            else:  # SHORT
                if price < peak:
                    pos['peak_price'] = price
                    peak = price
                trail_stop = peak * (1 + TP_TRAIL)
                hard_stop = entry * (1 + SL_PCT)
                if price >= trail_stop or price >= hard_stop:
                    pnl_pct = (entry - price) / entry * 100
                    total_pnl += pnl_pct
                    total_trades += 1
                    reason = '止盈' if price >= trail_stop and pnl_pct > 0 else '止损'
                    closed_positions.append((sym, direction, entry, price, pnl_pct, reason))
                    del positions[sym]

        # Send close alerts
        for sym, direction, entry, price, pnl_pct, reason in closed_positions:
            cn = sym.replace('USDT','')
            emoji = '\u2705' if pnl_pct > 0 else '\u274c'
            dir_cn = '做多' if direction == 'LONG' else '做空'
            t_str = datetime.now(BJT).strftime('%H:%M:%S')
            lines = [
                '\u2501' * 20,
                '  ' + emoji + ' 平仓 | ' + t_str,
                '  ' + cn + ' ' + dir_cn + ' | ' + reason,
                '  入场: ' + str(round(entry,4)) + ' \u2192 出场: ' + str(round(price,4)),
                '  盈亏: ' + ('+' if pnl_pct > 0 else '') + str(round(pnl_pct,2)) + '%',
                '  累计: ' + ('+' if total_pnl > 0 else '') + str(round(total_pnl,2)) + '% | ' + str(total_trades) + '笔',
                '\u2501' * 20
            ]
            feishu_app_send('\n'.join(lines))

        # === Signal detection ===
        for sym, (price, bid_qty, ask_qty) in price_map.items():
            if sym in positions:
                continue  # Already in a position
            if len(positions) >= MAX_POS:
                continue

            # Track price history
            if sym not in price_history:
                price_history[sym] = []
            hist = price_history[sym]
            vol_proxy = bid_qty + ask_qty
            hist.append((price, now, vol_proxy))
            while hist and len(hist[0]) >= 2 and hist[0][1] < now - 20:
                hist.pop(0)
            if len(hist) < 8:
                continue

            prices = [h[0] for h in hist]
            chg_pct = (prices[-1] - prices[0]) / prices[0] * 100

            # Volume surge
            vol_proxies = [h[2] for h in hist if len(h) >= 3]
            vol_surge = False
            if len(vol_proxies) >= 6:
                avg_vol = sum(vol_proxies[-6:-1]) / 5
                if avg_vol > 0 and vol_proxies[-1] / avg_vol > 2.5:
                    vol_surge = True

            # Trigger check
            if abs(chg_pct) >= 1.2:
                pass
            elif abs(chg_pct) >= 0.6 and vol_surge:
                pass
            else:
                continue

            # Sustained direction
            recent_deltas = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(-3, 0)]
            if chg_pct > 0 and any(d < 0 for d in recent_deltas):
                continue
            if chg_pct < 0 and any(d > 0 for d in recent_deltas):
                continue

            direction = 'LONG' if chg_pct > 0 else 'SHORT'
            ck = sym + '_' + direction
            if ck in last_alert and now - last_alert[ck] < COOLDOWN:
                continue
            last_alert[ck] = now

            # === Open position ===
            positions[sym] = {
                'direction': direction,
                'entry_price': price,
                'peak_price': price,
                'time': now
            }

            cn = sym.replace('USDT','')
            emoji = '\U0001f7e2' if direction == 'LONG' else '\U0001f534'
            dir_cn = '做多' if direction == 'LONG' else '做空'
            t_str = datetime.now(BJT).strftime('%H:%M:%S')
            vol_tag = ' \U0001f4ca' if vol_surge else ''

            lines = [
                '\u2501' * 20,
                '  ' + emoji + ' 开仓 | ' + t_str,
                '  ' + cn + ' ' + dir_cn + ' | ' + str(round(price,4)),
                '  \u2192 变动:' + str(round(chg_pct,1)) + '%' + vol_tag,
                '  \U0001f3af TP:跟踪回撤0.8% | \U0001f6d1 SL:1.5%',
                '  持仓:' + str(len(positions)) + '/' + str(MAX_POS) + ' | 累计:' + ('+' if total_pnl > 0 else '') + str(round(total_pnl,2)) + '%',
                '\u2501' * 20
            ]
            feishu_app_send('\n'.join(lines))
            print(f'[{t_str}] OPEN {cn} {dir_cn} @ {price:.4f} chg={chg_pct:+.1f}%')

    except Exception as e:
        pass

if __name__ == '__main__':
    print('sentinel v6 start |', datetime.now(BJT).strftime('%H:%M:%S'))
    feishu_send('\U0001f4c8 秒级纸盘v6上线 | 反转跟踪止盈0.8% | 硬止损1.5% | 最大5仓')
    scan_count = 0
    while True:
        t0 = time.time()
        scan()
        dt = time.time() - t0
        scan_count += 1
        if scan_count % 30 == 0:
            pos_info = ' '.join([f"{p['direction'][0]}{k.replace('USDT','')}" for k,p in positions.items()]) or '空仓'
            print(f'[{datetime.now(BJT).strftime("%H:%M:%S")}] heartbeat:{scan_count} pos:{len(positions)} [{pos_info}] pnl:{total_pnl:+.2f}%')
        time.sleep(max(0.5, 2 - dt))
