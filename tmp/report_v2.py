with open("/home/ubuntu/scripts/yaobi_v8.py") as f:
    lines = f.readlines()

# L128-139: the alert building (2 sections for long and short)
# L179-191: the message sending

# Replace alert building to include price
for i in range(128, 140):
    line = lines[i]
    if "LONG |" in line:
        lines[i] = '            alerts.append("LONG|" + sym + "|" + str(s["score"]) + "|" + str(s["cvd"]) + "|" + str(s["rsi"]) + "|" + str(s["price"]))\n'
    elif "SHORT |" in line:
        lines[i] = '            alerts.append("SHORT|" + sym + "|" + str(s["score"]) + "|" + str(s["cvd"]) + "|" + str(s["rsi"]) + "|" + str(s["price"]))\n'

# Replace message building (L179-L191)
msg_start = -1
msg_end = -1
for i, line in enumerate(lines):
    if "????" in line and i > 170:
        msg_start = i
    if msg_start >= 0 and "feishu_send" in line and i > msg_start:
        msg_end = i + 1
        break

if msg_start >= 0 and msg_end >= 0:
    new_msg = '''    # ??????????
    if alerts or closed or new_trades:
        t = now.strftime("%m/%d %H:%M")
        report = []
        report.append("??????????????????")
        report.append(f"  ?? ???? | {t}")
        report.append("??????????????????")

        longs = [a for a in alerts if a.startswith("LONG|")]
        shorts = [a for a in alerts if a.startswith("SHORT|")]

        if longs:
            report.append("  ?? ????")
            for a in longs[:5]:
                _, name, score, cvd, rsi, price = a.split("|")
                cn = name.replace("USDT","")
                report.append(f"    ?? {cn:<6} {score:>3}? CVD{cvd:>6}% RSI{rsi:>3} ${float(price):.4f}")

        if shorts:
            report.append("  ?? ????")
            for a in shorts[:5]:
                _, name, score, cvd, rsi, price = a.split("|")
                cn = name.replace("USDT","")
                report.append(f"    ?? {cn:<6} {score:>3}? CVD{cvd:>6}% RSI{rsi:>3} ${float(price):.4f}")

        if closed:
            report.append("  ?? ????")
            for sym, reason, pnl in closed:
                em = "?" if pnl > 0 else "?"
                cn = sym.replace("USDT","")
                report.append(f"    {em} {cn:<6} {reason} ??:{pnl:+.1f}%")

        pos_list = []
        for sym, p in list(positions.items())[:8]:
            cn = sym.replace("USDT","")
            d = "?" if p["direction"] == "long" else "?"
            pos_list.append(f"{d}{cn}")
        pos_str = " ".join(pos_list) if pos_list else "??"

        pnl_emoji = "??" if total_pnl >= 0 else "??"
        report.append("  ?????????????????")
        report.append(f"  ??: {len(positions)}/{MAX_POS} | {pnl_emoji} ??{total_pnl:+.1f}% | ?{state['trades']}?")
        report.append(f"  [{pos_str}]")
        report.append("??????????????????")

        feishu_send("\\n".join(report))
'''
    lines = lines[:msg_start] + [l + "\n" for l in new_msg.split("\n")] + lines[msg_end:]

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.writelines(lines)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
