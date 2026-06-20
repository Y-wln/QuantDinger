path = "/home/ubuntu/scripts/agents/ambush_scanner.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. OB threshold 22 -> 30
c = c.replace("if abs(imb) < 22:", "if abs(imb) < 30:")

# 2. Score threshold 25 -> 30
c = c.replace("if score >= 25:", "if score >= 30:")

# 3. Add per-coin cooldown check (5 min)
old_confirm = """                        if now_ts - prev_ts < 60:
                        # Confirmed! 2nd sighting"""
new_confirm = """                        if now_ts - prev_ts < 60:
                        # Check cooldown: don't repeat same coin+direction within 5 min
                        if pkey in _alerted and now_ts - _alerted[pkey] < 300:
                            del _pending[pkey]
                            continue
                        # Confirmed! 2nd sighting"""
c = c.replace(old_confirm, new_confirm)

# 4. Limit max signals per cycle to 3
old_push = "if signals:\n            signals.sort(key=lambda x: -x[4])"
new_push = "if signals:\n            signals.sort(key=lambda x: -x[4])\n            signals = signals[:3]  # v4: max 3 per cycle"
c = c.replace(old_push, new_push)

# 5. Update version
c = c.replace("[Ambush v3 PRIMARY]", "[Ambush v4 TIGHT]")
c = c.replace("Ambush v3 PRIMARY", "Ambush v4 TIGHT")
c = c.replace("[AmbushV3]", "[AmbushV4]")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("V4: OB>=30, score>=30, cooldown 5min, max 3/cycle")
