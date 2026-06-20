path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace the global BTC filter with per-coin trend check
# Instead of btc_regime controlling adaptive_min, let each coin pass based on its own trend
old_adaptive = """                    adaptive_min = 25
                    if btc_regime == "flat": adaptive_min = 35
                    elif btc_regime == "trending": adaptive_min = 18
                    if fng is not None:
                        if fng < 20: adaptive_min = max(12, adaptive_min - 8)"""

new_adaptive = """                    # v20: Per-coin adaptive threshold
                    # Check coin's own 1h trend - if trending, lower bar
                    coin_trending = False
                    try:
                        if k1 and len(k1) >= 6:
                            coin_1h = (float(k1[-1]["c"]) - float(k1[-6]["c"])) / float(k1[-6]["c"]) * 100
                            if abs(coin_1h) > 1.5:
                                coin_trending = True
                    except: pass
                    
                    adaptive_min = 25
                    if coin_trending: adaptive_min = 18  # own trend -> aggressive
                    elif btc_regime == "flat": adaptive_min = 28  # flat BTC, normal coin -> moderate
                    if btc_regime == "trending": adaptive_min = 20
                    if fng is not None:
                        if fng < 20: adaptive_min = max(14, adaptive_min - 6)"""

c = c.replace(old_adaptive, new_adaptive)

# Update version
c = c.replace("[YaobiV20]", "[YaobiV21]")
c = c.replace("Yaobi Pusher v20", "Yaobi Pusher v21")
c = c.replace("Yaobi Scan V20", "Yaobi Scan V21")
c = c.replace("YaobiPusher v20 FULL", "YaobiPusher v21 FULL")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("V21: Per-coin trend check, not global BTC gate")
