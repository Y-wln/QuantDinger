path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Return signed change from check_vol
old_check = "                    chg = abs((pn-p0)/p0*100) if p0 > 0 else 0\n                    if chg > 0.5: return (sym, chg)"
new_check = "                    chg_signed = ((pn-p0)/p0*100) if p0 > 0 else 0\n                    if abs(chg_signed) > 0.5: return (sym, chg_signed)"
content = content.replace(old_check, new_check)

# Fix 2: The exhaustion gate now works correctly with signed chg
# Replace the exhaustion gate to handle both directions properly
old_exhaust = """                    # v17: exhaustion gate - micro coins 1.5%, others 3%
                    exhaust_thresh = 1.5 if ("PUMP_DUMP" in str(reasons) or "PUMP_WARN" in str(reasons)) else 3.0
                    if vote_dir == "long" and chg > exhaust_thresh:
                        return None
                    if vote_dir == "short" and chg < -exhaust_thresh:
                        return None"""

new_exhaust = """                    # v17: exhaustion gate - micro coins 1.5%, others 3% (signed chg)
                    exhaust_thresh = 1.5 if ("PUMP_DUMP" in str(reasons) or "PUMP_WARN" in str(reasons) or "CUMUL_PUMP" in str(reasons)) else 3.0
                    if vote_dir == "long" and chg > exhaust_thresh:
                        return None
                    if vote_dir == "short" and chg < -exhaust_thresh:
                        return None"""

content = content.replace(old_exhaust, new_exhaust)

# Update version
content = content.replace("[YaobiV17.1]", "[YaobiV17.2]")
content = content.replace("Yaobi Pusher v17.1", "Yaobi Pusher v17.2")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Signed chg fix applied - short exhaustion now works")
