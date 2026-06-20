# Fix yaobi V19 - trend filter + BTC regime + score gate
path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Add 1h trend check in full_scan (after penalty locks, before signal emission)
# Find the section where score is calculated and add trend filter
old_trend = "                    # v10: weighted scoring + flip bonus + persistent penalty + exhaustion check"
new_trend = """                    # === v19: 1h trend filter - direction must align ===
                    if k1 and len(k1) >= 20:
                        k1_chg = (float(k1[-1]["c"]) - float(k1[-20]["c"])) / float(k1[-20]["c"]) * 100
                        if vote_dir == "long" and k1_chg < -0.3:
                            return None  # 1h downtrend, skip long
                        if vote_dir == "short" and k1_chg > 0.3:
                            return None  # 1h uptrend, skip short
                    
                    # v10: weighted scoring + flip bonus + persistent penalty + exhaustion check"""
c = c.replace(old_trend, new_trend)

# 2. Add BTC regime filter - at start of each cycle
old_btc = """        # Stage 1: volatility pre-filter (v6: 0.8%->0.5%)
        def check_vol(sym):"""
new_btc = """        # === v19: BTC regime filter - skip if BTC flat ===
        btc_flat = False
        try:
            k1_btc = fetch_klines("BTCUSDT", "1h", 6)
            if k1_btc and len(k1_btc) >= 6:
                btc_chg = (float(k1_btc[-1]["c"]) - float(k1_btc[-6]["c"])) / float(k1_btc[-6]["c"]) * 100
                if abs(btc_chg) < 0.5:
                    btc_flat = True
        except: pass
        
        # Stage 1: volatility pre-filter (v6: 0.8%->0.5%)
        def check_vol(sym):"""
c = c.replace(old_btc, new_btc)

# 3. Raise adaptive_min for flat BTC
old_adaptive = "                    adaptive_min = 20\n                    if fng is not None:\n                        if fng < 20: adaptive_min = 14"
new_adaptive = """                    adaptive_min = 20
                    if btc_flat: adaptive_min = 35  # v19: BTC flat -> only high confidence
                    if fng is not None:
                        if fng < 20: adaptive_min = 14"""
c = c.replace(old_adaptive, new_adaptive)

# Also raise base adaptive_min
old_adaptive2 = "adaptive_min = 20\n                    if btc_flat: adaptive_min = 35"
new_adaptive2 = "adaptive_min = 25\n                    if btc_flat: adaptive_min = 35"
c = c.replace(old_adaptive2, new_adaptive2)

# Update version
c = c.replace("[YaobiV18.1]", "[YaobiV19]")
c = c.replace("Yaobi Pusher v18.1", "Yaobi Pusher v19")
c = c.replace("Yaobi Scan V18", "Yaobi Scan V19")
c = c.replace("YaobiPusher v18 FULL", "YaobiPusher v19 FULL")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("V19: 1h trend filter + BTC regime + score>=25 (35 if flat)")
