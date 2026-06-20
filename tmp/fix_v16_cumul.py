# fix_yaobi_cumulative.py - add cumulative pump detection to V15
path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update detect_pump_dump to handle cumulative multi-candle pumps
old_func = """def detect_pump_dump(k5):
    \"\"\"v15: Detect pump-and-dump patterns. Single candle vol>8x + move>1.5% then reversal = distribution.\"\"\"
    if not k5 or len(k5) < 22: return False, None, ""
    last_v = float(k5[-2]["v"])
    last_o = float(k5[-2]["o"]); last_c = float(k5[-2]["c"])
    last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
    vols = [float(k["v"]) for k in k5[-22:-2]]
    avg_v = sum(vols) / max(len(vols), 1)
    if last_v > avg_v * 8 and last_chg > 1.5:
        curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
        curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
        if curr_chg < -0.3:
            return True, "pump_long", "PUMP_DUMP(x%.0f +%.1f%%_rev)" % (last_v/avg_v, last_chg)
        else:
            return True, "pump_long", "PUMP_WARN(x%.0f +%.1f%%)" % (last_v/avg_v, last_chg)
    if last_v > avg_v * 8 and last_chg < -1.5:
        curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
        curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
        if curr_chg > 0.3:
            return True, "pump_short", "PANIC_REV(x%.0f %.1f%%_rev)" % (last_v/avg_v, abs(last_chg))
    return False, None, """""

new_func = """def detect_pump_dump(k5):
    \"\"\"v16: Detect pump-and-dump patterns - single + cumulative multi-candle.\"\"\"
    if not k5 or len(k5) < 22: return False, None, ""
    last_v = float(k5[-2]["v"])
    last_o = float(k5[-2]["o"]); last_c = float(k5[-2]["c"])
    last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
    vols = [float(k["v"]) for k in k5[-22:-2]]
    avg_v = sum(vols) / max(len(vols), 1)
    
    # === Single candle pump (>8x vol + >1.5% move) ===
    if last_v > avg_v * 8 and last_chg > 1.5:
        curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
        curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
        if curr_chg < -0.3:
            return True, "pump_long", "PUMP_DUMP(x%.0f +%.1f%%_rev)" % (last_v/avg_v, last_chg)
        else:
            return True, "pump_long", "PUMP_WARN(x%.0f +%.1f%%)" % (last_v/avg_v, last_chg)
    if last_v > avg_v * 8 and last_chg < -1.5:
        curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
        curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
        if curr_chg > 0.3:
            return True, "pump_short", "PANIC_REV(x%.0f %.1f%%_rev)" % (last_v/avg_v, abs(last_chg))
    
    # === v16: Cumulative multi-candle pump (2-3 candles cumulative >2.5% + vol>5x) ===
    if len(k5) >= 5:
        c3_cum = 0.0
        for i in range(-4, -1):
            oi = float(k5[i]["o"]); ci = float(k5[i]["c"])
            c3_cum += (ci - oi) / oi * 100 if oi > 0 else 0
        v3 = sum(float(k5[i]["v"]) for i in range(-4, -1))
        v3_prev = sum(float(k5[i]["v"]) for i in range(-7, -4))
        v3_ratio = v3 / max(v3_prev, 0.001)
        if c3_cum > 2.5 and v3_ratio > 5.0:
            curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
            curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
            if curr_chg < -0.2:
                return True, "pump_long", "CUMUL_PUMP(3c+%.1f%%_x%.0f)" % (c3_cum, v3_ratio)
        if c3_cum < -2.5 and v3_ratio > 5.0:
            curr_o = float(k5[-1]["o"]); curr_c = float(k5[-1]["c"])
            curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
            if curr_chg > 0.2:
                return True, "pump_short", "CUMUL_DUMP(3c%.1f%%_x%.0f)" % (abs(c3_cum), v3_ratio)
    
    return False, None, """""

if old_func in content:
    content = content.replace(old_func, new_func)
    print("Pump detection upgraded to v16 (cumulative)")
else:
    print("WARNING: old function not found, searching...")
    # Try to find by function name
    idx = content.find("def detect_pump_dump(k5):")
    if idx >= 0:
        # Find end of function (next "def " or "while True:")
        end_idx = content.find("\ndef ", idx + 10)
        if end_idx < 0: end_idx = content.find("\nwhile True:", idx + 10)
        if end_idx > 0:
            content = content[:idx] + new_func + content[end_idx:]
            print("Pump detection upgraded via index search")

# 2. Update version strings
content = content.replace("# yaobi_pusher.py v15.0", "# yaobi_pusher.py v16.0")
content = content.replace("v15: pump-dump detection", "v16: pump-dump detection + cumulative")
content = content.replace("YaobiPusher v15 FULL", "YaobiPusher v16 FULL")
content = content.replace("Yaobi Pusher v15 | pump-dump", "Yaobi Pusher v16 | cumul-pump-detect")
content = content.replace("Yaobi Scan V15", "Yaobi Scan V16")
content = content.replace("[YaobiV15]", "[YaobiV16]")
content = content.replace("v15: exhaustion gate", "v16: exhaustion gate")
content = content.replace("v15: Pump/dump detection", "v16: Pump/dump detection")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("V16 upgrade complete")
