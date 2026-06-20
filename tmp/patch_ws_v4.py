# -*- coding: utf-8 -*-
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# 1. Threshold 0.6 -> 1.2
code = code.replace('if abs(chg_pct) < 0.6:', 'if abs(chg_pct) < 1.2:')

# 2. Cooldown 90 -> 180
code = code.replace('COOLDOWN = 90', 'COOLDOWN = 180')

# 3. Keep more history (10s -> 20s, need 8 points)
code = code.replace('while hist and hist[0][1] < now - 10:', 'while hist and hist[0][1] < now - 20:')
code = code.replace('if len(hist) < 4:', 'if len(hist) < 8:')

# 4. Add sustained check: last 3 readings must all be same direction
old_sust = '''            if abs(chg_pct) < 1.2:
                continue

            direction = 'LONG' if chg_pct > 0 else 'SHORT'
            ck = sym + '_' + direction'''

new_sust = '''            if abs(chg_pct) < 1.2:
                continue

            # Sustained: last 3 readings must all move in same direction
            recent_deltas = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(-3, 0)]
            if chg_pct > 0 and any(d < 0 for d in recent_deltas):
                continue
            if chg_pct < 0 and any(d > 0 for d in recent_deltas):
                continue

            direction = 'LONG' if chg_pct > 0 else 'SHORT'
            ck = sym + '_' + direction'''

code = code.replace(old_sust, new_sust)

# 5. Update startup message
code = code.replace('0.6%/10s触发', '1.2%/20s持续触发')

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('patched')
