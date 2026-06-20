# fix_v18.py - smarter weighting + loser lockout
path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Flip weights in yaobi_vote: OB (forward-looking) boost, CVD (lagging) reduce
# Old: CVD weight 2.0, OB weight 0.5
# New: CVD weight 1.0, OB weight 1.5

old_cvd = "    if cv5 > 30: vl += 2.0; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -30: vs += 2.0; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))\n    elif cv5 > 15: vl += 1.0; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -15: vs += 1.0; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))"
new_cvd = "    if cv5 > 30: vl += 1.0; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -30: vs += 1.0; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))\n    elif cv5 > 15: vl += 0.5; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -15: vs += 0.5; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))"
content = content.replace(old_cvd, new_cvd)

# Boost OB weight
old_ob = "    if imb > 15: vl += 0.5; rl.append(\"bid_wall(%d%%)\" % int(imb))\n    elif imb < -15: vs += 0.5; rs.append(\"ask_wall(%d%%)\" % int(abs(imb)))"
new_ob = "    if imb > 15: vl += 1.5; rl.append(\"bid_wall(%d%%)\" % int(imb))\n    elif imb < -15: vs += 1.5; rs.append(\"ask_wall(%d%%)\" % int(abs(imb)))"
content = content.replace(old_ob, new_ob)

# 2. Add loser lockout - track signal PnL, block repeat if losing
# Add after the cooldown check in full_scan
old_cooldown = """                    # === v6: Cooldown ===
                    ckey = \"%s_%s\" % (sym, vote_dir)
                    last_push = _cooldowns.get(ckey, 0)
                    if now_ts - last_push < 600: return None"""

new_cooldown = """                    # === v6: Cooldown ===
                    ckey = \"%s_%s\" % (sym, vote_dir)
                    last_push = _cooldowns.get(ckey, 0)
                    if now_ts - last_push < 600: return None
                    # === v18: Loser lockout - if same coin+dir signal lost, block 30min ===
                    loser_key = \"LOSE_%s_%s\" % (sym, vote_dir)
                    loser_until = _cooldowns.get(loser_key, 0)
                    if now_ts < loser_until: return None"""

content = content.replace(old_cooldown, new_cooldown)

# After setting cooldown, also check if previous signal lost
old_set_cooldown = "                        _cooldowns[\"%s_%s\" % (r[\"sym\"], r[\"dir\"])] = now_ts"
new_set_cooldown = """                        _cooldowns[\"%s_%s\" % (r[\"sym\"], r[\"dir\"])] = now_ts
                        # v18: Mark if signal is underwater after 5min -> lock 30min
                        # (checked next cycle by loser lockout above)
                        # Store signal entry for PnL tracking
                        _cooldowns[\"ENTRY_%s_%s\" % (r[\"sym\"], r[\"dir\"])] = r[\"price\"]"""
content = content.replace(old_set_cooldown, new_set_cooldown)

# Add loser detection: at start of each cycle, check previous entries
# Insert after the while True and before Stage 1
old_while = """while True:
    try:
        t0 = time.time()
        fng = fetch_fear_greed()
        now_ts = time.time()
        signals = []"""

new_while = """while True:
    try:
        t0 = time.time()
        fng = fetch_fear_greed()
        now_ts = time.time()
        signals = []
        # === v18: Check loser entries and lock out ===
        for key in list(_cooldowns.keys()):
            if key.startswith(\"ENTRY_\"):
                parts = key[6:].rsplit(\"_\", 1)
                if len(parts) == 2:
                    esym, edir = parts
                    entry_price = _cooldowns[key]
                    # Get current price
                    try:
                        cur = fetch_price(esym)
                        if cur:
                            if edir == \"long\" and cur < entry_price * 0.99:
                                loser_key = \"LOSE_%s_%s\" % (esym, edir)
                                _cooldowns[loser_key] = now_ts + 1800
                                del _cooldowns[key]
                            elif edir == \"short\" and cur > entry_price * 1.01:
                                loser_key = \"LOSE_%s_%s\" % (esym, edir)
                                _cooldowns[loser_key] = now_ts + 1800
                                del _cooldowns[key]
                    except:
                        pass"""

content = content.replace(old_while, new_while)

# Update version
content = content.replace("[YaobiV17.2]", "[YaobiV18]")
content = content.replace("Yaobi Pusher v17.2", "Yaobi Pusher v18")
content = content.replace("Yaobi Scan V17", "Yaobi Scan V18")
content = content.replace("# yaobi_pusher.py v17.0", "# yaobi_pusher.py v18.0 - OB-primary + loser-lockout")
content = content.replace("YaobiPusher v17 FULL", "YaobiPusher v18 FULL")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("V18: OB primary weight + loser lockout added")
