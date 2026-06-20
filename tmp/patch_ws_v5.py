# -*- coding: utf-8 -*-
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# Switch to bookTicker (has bid/ask volume for volume detection)
old_url = "/fapi/v1/ticker/price"
new_url = "/fapi/v1/ticker/bookTicker"
code = code.replace(old_url, new_url)

# Parse bookTicker fields (bidPrice, bidQty, askPrice, askQty)
old_parse = """            try:
                price = float(t.get('price',0))
                if price <= 0:
                    continue
            except:
                continue"""

new_parse = """            try:
                bid = float(t.get('bidPrice',0))
                ask = float(t.get('askPrice',0))
                price = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
                bid_qty = float(t.get('bidQty',0))
                ask_qty = float(t.get('askQty',0))
                if price <= 0:
                    continue
            except:
                continue"""

code = code.replace(old_parse, new_parse)

# Track volume too
old_hist_start = """            if sym not in price_history:
                price_history[sym] = []
            hist = price_history[sym]
            hist.append((price, now))"""

new_hist_start = """            if sym not in price_history:
                price_history[sym] = []
            hist = price_history[sym]
            # Track both price and volume (bid+ask qty as proxy for activity)
            vol_proxy = bid_qty + ask_qty
            hist.append((price, now, vol_proxy))"""

code = code.replace(old_hist_start, new_hist_start)

# Update history pruning (added vol_proxy field)
old_prune = "while hist and hist[0][1] < now - 20:"
new_prune = "while hist and len(hist[0]) >= 2 and hist[0][1] < now - 20:"
code = code.replace(old_prune, new_prune)

# Add volume surge detection alongside price
old_check = """            if abs(chg_pct) < 1.2:
                continue

            # Sustained: last 3 readings must all move in same direction
            recent_deltas = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(-3, 0)]
            if chg_pct > 0 and any(d < 0 for d in recent_deltas):
                continue
            if chg_pct < 0 and any(d > 0 for d in recent_deltas):
                continue"""

new_check = """            # Volume surge detection
            vol_proxies = [h[2] for h in hist if len(h) >= 3]
            vol_surge = False
            if len(vol_proxies) >= 6:
                avg_vol = sum(vol_proxies[-6:-1]) / 5
                if avg_vol > 0 and vol_proxies[-1] / avg_vol > 2.5:
                    vol_surge = True

            # Trigger: either strong price (1.2%) OR moderate price (0.6%) + volume surge
            if abs(chg_pct) >= 1.2:
                pass  # Strong price move, proceed
            elif abs(chg_pct) >= 0.6 and vol_surge:
                pass  # Moderate move with volume confirmation
            else:
                continue

            # Sustained: last 3 readings must all move in same direction
            recent_deltas = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(-3, 0)]
            if chg_pct > 0 and any(d < 0 for d in recent_deltas):
                continue
            if chg_pct < 0 and any(d > 0 for d in recent_deltas):
                continue"""

code = code.replace(old_check, new_check)

# Update alert message to show volume info
old_alert_msg = "                '  \\u2192 10s变动: ' + str(round(chg_pct, 1)) + '%',"
new_alert_msg = "                '  \\u2192 20s变动: ' + str(round(chg_pct, 1)) + '%' + (' \\U0001f4ca' if vol_surge else ''),"
code = code.replace(old_alert_msg, new_alert_msg)

# Update version
code = code.replace('v3', 'v5')

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('patched to v5')
