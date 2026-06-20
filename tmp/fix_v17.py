# fix_yaobi_v17.py - faster scan + 1m pre-warning
path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Reduce scan interval: 120s -> 30s
content = content.replace("time.sleep(max(10, 120 - elapsed))", "time.sleep(max(5, 30 - elapsed))")

# 2. Add 1m fast pre-scan: after the volatility pre-filter, do a 1m pump check
# Find the "Stage 1: volatility pre-filter" section and add 1m fast check after it
old_candidates_sort = 'candidates.sort(key=lambda x: -x[1])\n        candidates = candidates[:12]'

new_fast_scan = '''        # === v17: 1m fast pre-scan for pump/dump on volatile coins ===
        fast_warnings = []
        if candidates:
            def fast_check_1m(sym_chg):
                sym, _ = sym_chg
                try:
                    k1m = fetch_klines(sym, "1m", 30)
                    if not k1m or len(k1m) < 20: return None
                    # Fast pump check on 1m
                    last_v = float(k1m[-2]["v"])
                    last_o = float(k1m[-2]["o"]); last_c = float(k1m[-2]["c"])
                    last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
                    vols = [float(k["v"]) for k in k1m[-20:-2]]
                    avg_v = sum(vols) / max(len(vols), 1)
                    if last_v > avg_v * 8 and abs(last_chg) > 1.0:
                        price = fetch_price(sym)
                        return (sym, "PUMP_UP" if last_chg > 0 else "DUMP_DOWN", last_chg, last_v/avg_v, price)
                    # Cumulative 3x1m
                    if len(k1m) >= 5:
                        c3 = sum((float(k1m[i]["c"])-float(k1m[i]["o"]))/float(k1m[i]["o"])*100 for i in range(-4,-1) if float(k1m[i]["o"])>0)
                        v3 = sum(float(k1m[i]["v"]) for i in range(-4,-1))
                        vp = sum(float(k1m[i]["v"]) for i in range(-7,-4))
                        if abs(c3) > 2.0 and v3/max(vp,0.001) > 4:
                            price = fetch_price(sym)
                            return (sym, "CUMUL_UP" if c3>0 else "CUMUL_DOWN", c3, v3/max(vp,0.001), price)
                except: pass
                return None
            
            fast_futures = {ex.submit(fast_check_1m, c): c for c in candidates[:8]}
            for f in as_completed(fast_futures, timeout=30):
                r = f.result()
                if r:
                    sym, ptype, chg, vratio, price = r
                    sym_short = sym.replace("USDT","")
                    fast_warnings.append("[1m] %s %s %.1f%% x%.0f @%s" % (sym_short, ptype, chg, vratio, price))
            if fast_warnings:
                print("[YaobiV17] 1m fast warnings: " + "; ".join(fast_warnings[:5]))
        
        candidates.sort(key=lambda x: -x[1])
        candidates = candidates[:12]'''

content = content.replace(old_candidates_sort, new_fast_scan)

# 3. Update version
content = content.replace("# yaobi_pusher.py v16.0", "# yaobi_pusher.py v17.0")
content = content.replace("v16: pump-dump detection + cumulative", "v17: 30s-cycle + 1m fast pre-scan")
content = content.replace("YaobiPusher v16 FULL", "YaobiPusher v17 FULL")
content = content.replace("Yaobi Pusher v16 | cumul-pump-detect", "Yaobi Pusher v17 | 30s-cycle +1m-fast")
content = content.replace("Yaobi Scan V16", "Yaobi Scan V17")
content = content.replace("[YaobiV16]", "[YaobiV17]")
content = content.replace("v16: exhaustion gate", "v17: exhaustion gate")
content = content.replace("v16: Pump/dump detection", "v17: Pump/dump detection")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("V17 upgrade complete: 30s cycle + 1m fast pre-scan")
