# Fix 1: Yaobi - lower gate 3->2, CVD 1.5->1.8
path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Lower confirmation gate from 3 to 2
c = c.replace("if confirmations < 3:", "if confirmations < 2:")

# CVD weight 1.5->1.8
c = c.replace(
    "if cv5 > 30: vl += 1.5; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -30: vs += 1.5; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))\n    elif cv5 > 15: vl += 0.8; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -15: vs += 0.8; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))",
    "if cv5 > 30: vl += 1.8; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -30: vs += 1.8; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))\n    elif cv5 > 15: vl += 0.9; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -15: vs += 0.9; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))"
)
c = c.replace("[YaobiV18]", "[YaobiV18.1]")
c = c.replace("Yaobi Pusher v18", "Yaobi Pusher v18.1")
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Yaobi: gate 3->2, CVD 1.5->1.8")

# Fix 2+3: MerCu - cooldown + score threshold + stock filter
path2 = "/home/ubuntu/scripts/agents/mercu_signals.py"
with open(path2, "r", encoding="utf-8-sig") as f:
    c2 = f.read()

# Add cooldown tracking
old_while = "while True:\n    try:"
new_while = """_mercu_cooldown = {}

while True:
    try:"""
c2 = c2.replace(old_while, new_while)

# Score threshold 5->6
c2 = c2.replace("if score >= 5:", "if score >= 6:")

# Add cooldown check + stock filter before signal append
old_append = 'signals.append({"sym": sym, "dir": direction, "score": score, "reasons": reasons, "price": price or 0})'
new_append = '''# v3: cooldown + stock filter
                if sym in ("SPCX","VELVET","INTC","MU","XAUT"): continue
                ck2 = sym + "_" + direction
                last_mercu = _mercu_cooldown.get(ck2, 0)
                if time.time() - last_mercu < 600: continue
                _mercu_cooldown[ck2] = time.time()
                signals.append({"sym": sym, "dir": direction, "score": score, "reasons": reasons, "price": price or 0})'''
c2 = c2.replace(old_append, new_append)

# Update version
c2 = c2.replace('"""mercu_signals.py v2', '"""mercu_signals.py v3')
c2 = c2.replace("MerCu v2 |", "MerCu v3 | +cooldown +score6")

with open(path2, "w", encoding="utf-8") as f:
    f.write(c2)
print("MerCu: cooldown 10min + score>=6 + stock filter")
