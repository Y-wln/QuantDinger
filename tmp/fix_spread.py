# -*- coding: utf-8 -*-
import os
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# Fix spread filter - use price spread not quantity spread
old_spread = "            # Spread filter: skip if bid-ask > 0.5% (illiquid)\n            spread_pct = (ask_qty - bid_qty) / ((bid_qty + ask_qty) / 2) * 100 if (bid_qty + ask_qty) > 0 else 0\n            if spread_pct > 50:\n                continue"
new_spread = "            # Spread filter: skip if bid-ask spread > 0.5%\n            spread_pct = (ask - bid) / bid * 100 if bid > 0 else 0\n            if spread_pct > 0.5:\n                continue"

code = code.replace(old_spread, new_spread)

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('fixed spread')
