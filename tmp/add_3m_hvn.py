import py_compile, os

# ====== 1. hermes_core.py: add HVN/LVN function ======
with open('/home/ubuntu/scripts/agents/hermes_core.py', 'r') as f:
    content = f.read()

hvn_func = '''
# HVN/LVN Volume Profile
def volume_profile_zones(klines, bins=10):
    """Find High Volume Nodes and Low Volume Nodes from recent klines."""
    if len(klines) < 20:
        return None
    closes = [k["c"] for k in klines]
    highs = [k["h"] for k in klines[-30:]]
    lows = [k["l"] for k in klines[-30:]]
    volumes = [k["v"] for k in klines[-30:]]
    price_min = min(lows)
    price_max = max(highs)
    if price_max <= price_min:
        return None
    bin_size = (price_max - price_min) / bins
    histogram = [0] * bins
    for i, k in enumerate(klines[-30:]):
        mid = (k["h"] + k["l"]) / 2
        idx = min(bins-1, max(0, int((mid - price_min) / bin_size)))
        histogram[idx] += volumes[i]
    avg_vol = sum(histogram) / bins if bins > 0 else 1
    hvns = []
    lvns = []
    for i, v in enumerate(histogram):
        zone_price = round(price_min + bin_size * (i + 0.5), 4)
        if v > avg_vol * 1.5:
            hvns.append((zone_price, round(v,0)))
        elif v < avg_vol * 0.5:
            lvns.append((zone_price, round(v,0)))
    current = closes[-1]
    in_hvn = any(abs(current - p) / current < 0.01 for p, _ in hvns)
    nearest_hvn = min(hvns, key=lambda x: abs(current-x[0]))[0] if hvns else None
    nearest_lvn = min(lvns, key=lambda x: abs(current-x[0]))[0] if lvns else None
    return {
        "hvns": hvns[:5], "lvns": lvns[:5],
        "current_in_hvn": in_hvn,
        "nearest_hvn": nearest_hvn,
        "nearest_lvn": nearest_lvn,
        "current": round(current, 4)
    }

print("[HermesCore] v2.2 - HVN/LVN volume profile loaded")
'''

# Insert before the last print statement
old_last = "print('[HermesCore] v2.1 - entry quality filter loaded')"
content = content.replace(old_last, hvn_func)
print('hermes_core: HVN/LVN added')

with open('/home/ubuntu/scripts/agents/hermes_core.py', 'w') as f:
    f.write(content)

py_compile.compile('/home/ubuntu/scripts/agents/hermes_core.py', doraise=True)
print('hermes_core: compiled OK')

# ====== 2. agent_technical.py: add 3m confirmation + HVN filter ======
with open('/home/ubuntu/scripts/agents/agent_technical.py', 'r') as f:
    content = f.read()

# Add 3m kline fetch in the analyze function
old_kl = "k5 = results.get('5m', [])"
new_kl = "k5 = results.get('5m', [])\n        k3 = results.get('3m', [])"
content = content.replace(old_kl, new_kl)

# Add 3m to the tasks dict
old_tasks = "\"5m\": (sym, '5m', 200), \"15m\": (sym, '15m', 100)"
new_tasks = "\"5m\": (sym, '5m', 200), \"3m\": (sym, '3m', 150), \"15m\": (sym, '15m', 100)"
content = content.replace(old_tasks, new_tasks)

# Add 3m+5m confirmation check in launch detection area
old_launch = "# ====== ????? - ????? (30?) ======"
new_launch = """        # ====== 3m+5m??????? ======
        cv3 = calc_cvd(k3[-6:], 4) if k3 and len(k3) >= 6 else 0
        cv5 = calc_cvd(klines_5m[-6:], 4) if klines_5m and len(klines_5m) >= 6 else 0
        if cv3 > 12 and cv5 > 12:
            score += 10; details['3m5m_res'] = '+10 3m+5m????'
            leading_signals.append('3m+5m????')
        elif cv3 < -12 and cv5 < -12:
            score -= 10; details['3m5m_res'] = '-10 3m+5m????'
            leading_signals.append('3m+5m????')
        elif (cv3 > 12 and cv5 < -5) or (cv3 < -12 and cv5 > 5):
            score += 3 if score > 0 else -3
            details['3m5m_div'] = '3m5m?? ????'

        # ====== ????? - ????? (30?) ======"""
content = content.replace(old_launch, new_launch)

# Add HVN/LVN filter in entry quality
old_entry = "        # ====== ?????? (????) ======"
new_entry = """        # ====== HVN/LVN ??????? ======
        try:
            from hermes_core import volume_profile_zones
            vp = volume_profile_zones(k4)
            if vp:
                if vp['current_in_hvn']:
                    score = score * 0.7 if abs(score) > 20 else score * 0.5
                    details['hvn'] = 'HVN?? ????'
                    leading_signals.append('HVN?????-??')
                elif vp['nearest_lvn'] and abs(vp['current'] - vp['nearest_lvn']) / vp['current'] < 0.015:
                    score = score * 1.2 if abs(score) > 15 else score
                    details['lvn'] = 'LVN?? ????'
        except Exception:
            pass

        # ====== ?????? (????) ======"""
content = content.replace(old_entry, new_entry)

with open('/home/ubuntu/scripts/agents/agent_technical.py', 'w') as f:
    f.write(content)

py_compile.compile('/home/ubuntu/scripts/agents/agent_technical.py', doraise=True)
print('agent_technical: 3m+HVN added, compiled OK')

# ====== 3. signal_pusher.py: add 3m confirmation ======
with open('/home/ubuntu/scripts/agents/signal_pusher.py', 'r') as f:
    content = f.read()

old_scan = "def quick_launch_score(sym):"
new_scan = """def quick_launch_score(sym):
    score = 0
    reasons = []
    k5 = fetch_klines(sym, '5m', 12)
    k3 = fetch_klines(sym, '3m', 12)
    if len(k5) < 8:
        return 0, []
    cv5 = calc_cvd(k5, 4)
    cv3 = calc_cvd(k3, 4) if len(k3) >= 8 else 0
    # 3m+5m must agree
    if cv5 > 20 and cv3 < 0:
        return 0, []
    if cv5 < -20 and cv3 > 0:
        return 0, []
    # Original scoring continues..."""

# Find and replace the scoring start
old_scoring = "    score = 0\n    reasons = []\n    k5 = fetch_klines(sym, '5m', 12)\n    if len(k5) < 8:\n        return 0, []\n    cv5 = calc_cvd(k5, 4)"
new_scoring = "    score = 0\n    reasons = []\n    k5 = fetch_klines(sym, '5m', 12)\n    k3 = fetch_klines(sym, '3m', 12)\n    if len(k5) < 8:\n        return 0, []\n    cv5 = calc_cvd(k5, 4)\n    cv3 = calc_cvd(k3, 4) if len(k3) >= 8 else 0\n    # 3m+5m direction must agree\n    if cv5 > 20 and cv3 < 0: return 0, []\n    if cv5 < -20 and cv3 > 0: return 0, []"

content = content.replace(old_scoring, new_scoring)
print('signal_pusher: 3m confirmation added')

with open('/home/ubuntu/scripts/agents/signal_pusher.py', 'w') as f:
    f.write(content)

py_compile.compile('/home/ubuntu/scripts/agents/signal_pusher.py', doraise=True)
print('signal_pusher: compiled OK')

print('\nDone! 3m + HVN/LVN added to all 3 files')
