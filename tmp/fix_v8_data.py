# -*- coding: utf-8 -*-
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# Fix: store bid/ask prices in price_map for spread calculation
old_map = "            price_map[sym] = (price, bid_qty, ask_qty)"
new_map = "            price_map[sym] = (price, bid_qty, ask_qty, bid, ask)"
code = code.replace(old_map, new_map)

# Fix: unpack all 5 values in signal detection loop
old_unpack = "        for sym, (price, bid_qty, ask_qty) in price_map.items():"
new_unpack = "        for sym, (price, bid_qty, ask_qty, bid, ask) in price_map.items():"
code = code.replace(old_unpack, new_unpack)

# Fix: also check position management loop uses correct unpacking
# Position management uses the same price_map but might access differently
old_pos_loop = "            if sym not in price_map: continue\n            price, _, _ = price_map[sym]"
new_pos_loop = "            if sym not in price_map: continue\n            price, _, _, _, _ = price_map[sym]"
code = code.replace(old_pos_loop, new_pos_loop)

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('fixed data structure')
