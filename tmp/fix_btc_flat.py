path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Find where to insert btc_flat initialization
old = "        # Stage 1: volatility pre-filter"
new = """        # === v19: BTC regime filter ===
        btc_flat = False
        try:
            k1_btc = fetch_klines("BTCUSDT", "1h", 6)
            if k1_btc and len(k1_btc) >= 6:
                btc_chg = abs((float(k1_btc[-1]["c"]) - float(k1_btc[-6]["c"])) / float(k1_btc[-6]["c"]) * 100)
                if btc_chg < 0.5:
                    btc_flat = True
                    print("[YaobiV19] BTC flat (%.1f%%), high-confidence only" % btc_chg)
        except: pass
        
        # Stage 1: volatility pre-filter"""
c = c.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("btc_flat init added")
