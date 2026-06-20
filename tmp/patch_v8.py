# -*- coding: utf-8 -*-
import os
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# 1. Add time-based exit (3 min max hold)
old_trail = "                trail_stop = peak * (1 - TP_TRAIL)\n                hard_stop = entry * (1 - SL_PCT)\n                if price <= trail_stop or price <= hard_stop:"
new_trail = "                trail_stop = peak * (1 - TP_TRAIL)\n                hard_stop = entry * (1 - SL_PCT)\n                time_exit = now - pos.get('time', now) > 180 and price < entry  # 3min no profit -> exit\n                if price <= trail_stop or price <= hard_stop or time_exit:"
code = code.replace(old_trail, new_trail)

old_trail_s = "                trail_stop = peak * (1 + TP_TRAIL)\n                hard_stop = entry * (1 + SL_PCT)\n                if price >= trail_stop or price >= hard_stop:"
new_trail_s = "                trail_stop = peak * (1 + TP_TRAIL)\n                hard_stop = entry * (1 + SL_PCT)\n                time_exit = now - pos.get('time', now) > 180 and price > entry\n                if price >= trail_stop or price >= hard_stop or time_exit:"
code = code.replace(old_trail_s, new_trail_s)

# Update exit reason for time exit
old_reason_long = "                    reason = '止盈' if price <= trail_stop and pnl_pct > 0 else '止损'"
new_reason_long = "                    reason = '止盈' if (price <= trail_stop and pnl_pct > 0) else ('超时' if time_exit else '止损')"
code = code.replace(old_reason_long, new_reason_long)

old_reason_short = "                    reason = '止盈' if price >= trail_stop and pnl_pct > 0 else '止损'"
new_reason_short = "                    reason = '止盈' if (price >= trail_stop and pnl_pct > 0) else ('超时' if time_exit else '止损')"
code = code.replace(old_reason_short, new_reason_short)

# 2. Add spread filter
old_entry_check = "            # Trigger check\n            if abs(chg_pct) >= 1.2:"
new_entry_check = "            # Spread filter: skip if bid-ask > 0.5% (illiquid)\n            spread_pct = (ask_qty - bid_qty) / ((bid_qty + ask_qty) / 2) * 100 if (bid_qty + ask_qty) > 0 else 0\n            if spread_pct > 50:\n                continue\n\n            # Trigger check\n            if abs(chg_pct) >= 1.2:"
code = code.replace(old_entry_check, new_entry_check)

# 3. Add momentum acceleration check
old_open_log = "            log_trade({'sym': sym, 'dir': direction, 'entry': price, 'chg': round(chg_pct,1), 'vol_surge': vol_surge, 'time': datetime.now(BJT).isoformat(), 'type': 'entry'})"
new_open_log = "            accel = round(chg_pct / len(hist), 2) if len(hist) > 0 else 0\n            log_trade({'sym': sym, 'dir': direction, 'entry': price, 'chg': round(chg_pct,1), 'vol_surge': vol_surge, 'accel': accel, 'spread': round(spread_pct,1), 'time': datetime.now(BJT).isoformat(), 'type': 'entry'})"
code = code.replace(old_open_log, new_open_log)

# 4. Update version
code = code.replace('v7', 'v8')
code = code.replace('v6', 'v8')

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('patched to v8')
