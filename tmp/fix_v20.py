path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace the simple btc_flat with a 3-tier regime
old_btc = """        # === v19: BTC regime filter ===
        btc_flat = False
        try:
            k1_btc = fetch_klines("BTCUSDT", "1h", 6)
            if k1_btc and len(k1_btc) >= 6:
                btc_chg = abs((float(k1_btc[-1]["c"]) - float(k1_btc[-6]["c"])) / float(k1_btc[-6]["c"]) * 100)
                if btc_chg < 0.5:
                    btc_flat = True
                    print("[YaobiV19] BTC flat (%.1f%%), high-confidence only" % btc_chg)
        except: pass"""

new_btc = """        # === v20: 3-tier BTC regime ===
        btc_regime = "normal"  # normal / flat / trending
        btc_signal = 0  # positive = bullish bias, negative = bearish
        try:
            k1_btc = fetch_klines("BTCUSDT", "1h", 12)
            if k1_btc and len(k1_btc) >= 6:
                # Multi-timeframe check
                btc_6h = (float(k1_btc[-1]["c"]) - float(k1_btc[-6]["c"])) / float(k1_btc[-6]["c"]) * 100
                btc_12h = (float(k1_btc[-1]["c"]) - float(k1_btc[-12]["c"])) / float(k1_btc[-12]["c"]) * 100 if len(k1_btc)>=12 else btc_6h
                btc_signal = btc_6h
                if abs(btc_6h) < 0.5:
                    btc_regime = "flat"
                    print("[YaobiV20] BTC flat (6h:%.1f%%, 12h:%.1f%%), high-conf only" % (btc_6h, btc_12h))
                elif abs(btc_6h) > 2.0:
                    btc_regime = "trending"
                    print("[YaobiV20] BTC trending (6h:%+.1f%%), aggressive mode" % btc_6h)
                else:
                    print("[YaobiV20] BTC normal (6h:%+.1f%%)" % btc_6h)
        except: pass"""

c = c.replace(old_btc, new_btc)

# Replace the adaptive_min logic with 3-tier
old_adaptive = """                    adaptive_min = 25
                    if btc_flat: adaptive_min = 35  # v19: BTC flat -> only high confidence
                    if fng is not None:
                        if fng < 20: adaptive_min = 14"""

new_adaptive = """                    adaptive_min = 25
                    if btc_regime == "flat": adaptive_min = 35
                    elif btc_regime == "trending": adaptive_min = 18
                    if fng is not None:
                        if fng < 20: adaptive_min = max(12, adaptive_min - 8)"""

c = c.replace(old_adaptive, new_adaptive)

# Also add directional bias in trending mode: if BTC trending up, penalize shorts; if down, penalize longs
old_penalty = "                    if k1 and len(k1) >= 20:\n                        from hermes_core import detect_structure\n                        s4, _ = detect_structure(k1)\n                        if vote_dir == \"long\" and s4 == \"down\":\n                            penalty += 6\n                        if vote_dir == \"short\" and s4 == \"up\":\n                            penalty += 6"

new_penalty = """                    if k1 and len(k1) >= 20:
                        from hermes_core import detect_structure
                        s4, _ = detect_structure(k1)
                        if vote_dir == "long" and s4 == "down":
                            penalty += 6
                        if vote_dir == "short" and s4 == "up":
                            penalty += 6
                    # v20: BTC directional bias in trending mode
                    if btc_regime == "trending":
                        if vote_dir == "long" and btc_signal < -1.5:
                            penalty += 4
                        if vote_dir == "short" and btc_signal > 1.5:
                            penalty += 4"""

c = c.replace(old_penalty, new_penalty)

# Version
c = c.replace("[YaobiV19]", "[YaobiV20]")
c = c.replace("Yaobi Pusher v19", "Yaobi Pusher v20")
c = c.replace("Yaobi Scan V19", "Yaobi Scan V20")
c = c.replace("YaobiPusher v19 FULL", "YaobiPusher v20 FULL")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("V20: 3-tier BTC regime (flat/normal/trending) + directional bias")
