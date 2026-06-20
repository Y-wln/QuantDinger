# -*- coding: utf-8 -*-
import json, os
from datetime import datetime

p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

trade_log_path = '/home/ubuntu/scripts/trade_log.json'

# Add trade logging imports and path
old_imports = "from hermes_core import feishu_app_send, feishu_send, proxy_mgr, BINANCE_F"
new_imports = "from hermes_core import feishu_app_send, feishu_send, proxy_mgr, BINANCE_F\nTRADE_LOG = '" + trade_log_path + "'"
code = code.replace(old_imports, new_imports)

# Add log_trade function
log_func = '''
def log_trade(entry):
    try:
        logs = []
        if os.path.exists(TRADE_LOG):
            with open(TRADE_LOG) as f:
                logs = json.load(f)
        logs.append(entry)
        with open(TRADE_LOG, 'w') as f:
            json.dump(logs, f, indent=2, default=str)
    except:
        pass

'''
code = code.replace("def scan():", log_func + "def scan():")

# Log close events
old_close = "                    del positions[sym]"
# For long close
old_long_close = "                    reason = '止盈' if price <= trail_stop and pnl_pct > 0 else '止损'\n                    closed_positions.append((sym, direction, entry, price, pnl_pct, reason))\n                    del positions[sym]"
new_long_close = "                    reason = '止盈' if price <= trail_stop and pnl_pct > 0 else '止损'\n                    log_trade({'sym': sym, 'dir': direction, 'entry': entry, 'exit': price, 'pnl': round(pnl_pct,2), 'reason': reason, 'time': datetime.now(BJT).isoformat(), 'type': 'exit'})\n                    closed_positions.append((sym, direction, entry, price, pnl_pct, reason))\n                    del positions[sym]"
code = code.replace(old_long_close, new_long_close)

# For short close
old_short_close = "                    reason = '止盈' if price >= trail_stop and pnl_pct > 0 else '止损'\n                    closed_positions.append((sym, direction, entry, price, pnl_pct, reason))\n                    del positions[sym]"
new_short_close = "                    reason = '止盈' if price >= trail_stop and pnl_pct > 0 else '止损'\n                    log_trade({'sym': sym, 'dir': direction, 'entry': entry, 'exit': price, 'pnl': round(pnl_pct,2), 'reason': reason, 'time': datetime.now(BJT).isoformat(), 'type': 'exit'})\n                    closed_positions.append((sym, direction, entry, price, pnl_pct, reason))\n                    del positions[sym]"
code = code.replace(old_short_close, new_short_close)

# Log open events
old_open = "            positions[sym] = {"
new_open = "            log_trade({'sym': sym, 'dir': direction, 'entry': price, 'chg': round(chg_pct,1), 'vol_surge': vol_surge, 'time': datetime.now(BJT).isoformat(), 'type': 'entry'})\n            positions[sym] = {"
code = code.replace(old_open, new_open)

# Update version
code = code.replace('v6', 'v7')
code = code.replace('v5', 'v7')

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('patched to v7 with trade logging')
