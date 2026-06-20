path = "/home/ubuntu/scripts/agents/selfcheck.py"
with open(path, encoding="utf-8-sig") as f:
    c = f.read()
old = 'for fname, max_age in [("momentum_15m.json",120),("momentum_4h.json",300),\n                        ("anomaly-v4_100.json",120),("rank.json",300),("surge_5.json",120)]:'
new = 'for fname, max_age in [("momentum_window_15m.json",120),("momentum_window_4h.json",300),\n                        ("anomaly-v4_limit_100.json",120),("rank.json",300),("surge_limit_5.json",120)]:'
c = c.replace(old, new)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("selfcheck fixed")
