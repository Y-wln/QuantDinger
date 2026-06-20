# fix_yaobi_v16.py - replace garbled display section with clean English+emoji
# All Unicode chars are in \U format (ASCII-safe)

NEW_DISPLAY = """        # Push
        if signals:
            signals.sort(key=lambda x: -x["score"])
            t = datetime.now(BJT).strftime("%m/%d %H:%M")
            lines = ["----------------", "  \U0001f3af Yaobi Scan V15 | %s" % t, "----------------"]
            
            longs = [s for s in signals if s["dir"] == "long"]
            shorts = [s for s in signals if s["dir"] == "short"]
            
            if longs:
                lines.append("  \U0001f7e2 === LONG ===")
                for s in longs[:5]:
                    sym = s["sym"].replace("USDT", "")
                    reason_str = " | ".join(s.get("reasons", [])[:3])
                    badges = ""
                    if s.get("is_flip"): badges += "\U0001f6a8FLIP "
                    if s.get("streak", 1) >= 3: badges += "\U0001f525PERSIST "
                    ob = s.get("ob_imb", 0)
                    ob_str = " OB:%+d%%" % int(ob) if abs(ob) > 10 else ""
                    cross_badge = get_badge(sym, "long", "yaobi")
                    lines.append("    LONG %-6s %3dpt $%s %s%s%s" % (sym, s["score"], s["price"], badges, cross_badge, ob_str))
                    if reason_str:
                        lines.append("      -> %s" % reason_str[:70])
            
            if shorts:
                lines.append("  \U0001f534 === SHORT ===")
                for s in shorts[:5]:
                    sym = s["sym"].replace("USDT", "")
                    reason_str = " | ".join(s.get("reasons", [])[:3])
                    badges = ""
                    if s.get("is_flip"): badges += "\U0001f6a8FLIP "
                    if s.get("streak", 1) >= 3: badges += "\U0001f525PERSIST "
                    ob = s.get("ob_imb", 0)
                    ob_str = " OB:%+d%%" % int(ob) if abs(ob) > 10 else ""
                    cross_badge = get_badge(sym, "short", "yaobi")
                    lines.append("    SHORT %-6s %3dpt $%s %s%s%s" % (sym, s["score"], s["price"], badges, cross_badge, ob_str))
                    if reason_str:
                        lines.append("      -> %s" % reason_str[:70])
            
            lines.append("----------------")
"""

path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8-sig") as f:
    content = f.read()

# Find the Push section: from "# Push" to the cross_sigs/feishu line
old_start = content.find("        # Push")
old_end = content.find("            cross_sigs = [")
if old_start < 0 or old_end < 0:
    print("ERROR: cannot find Push section")
    exit(1)

# Replace
new_content = content[:old_start] + NEW_DISPLAY + content[old_end:]
with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("V15 display section replaced with English+emoji")
