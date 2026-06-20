with open("/home/ubuntu/scripts/yaobi_v8.py") as f:
    lines = f.readlines()

# We know the exact lines: "????" block is at L179-L192 (0-indexed: 178-191)
# L178: "    # ????"
# L191: "        feishu_send('\\n'.join(msgs))"

# Verify
print(f"L179: {lines[178].strip()}")
print(f"L192: {lines[191].strip()}")

# Build replacement
new_block = '''    # ??????????
    if alerts or closed or new_trades:
        t = now.strftime("%m/%d %H:%M")
        report = []
        report.append("??????????????????")
        report.append(f"  ?? ???? | {t}")
        report.append("??????????????????")

        if alerts:
            longs = [a for a in alerts if "LONG" in a]
            shorts = [a for a in alerts if "SHORT" in a]

            if longs:
                report.append("  ?? ????")
                for a in longs[:5]:
                    parts = a.replace("?? ","").split(" | ")
                    name = parts[0].replace(" LONG","")
                    score = parts[1].replace("?","")
                    cvd = parts[2].replace("CVD:","")
                    rsi = parts[3].replace("RSI:","")
                    price_str = ""
                    for s in signals:
                        if s["sym"].replace("USDT","") == name:
                            price_str = " ${:.4f}".format(s["price"])
                            break
                    report.append("    ?? {:<6} {:>3}? CVD{:>6} RSI{:>3}{}".format(name, score, cvd, rsi, price_str))

            if shorts:
                report.append("  ?? ????")
                for a in shorts[:5]:
                    parts = a.replace("?? ","").split(" | ")
                    name = parts[0].replace(" SHORT","")
                    score = parts[1].replace("?","")
                    cvd = parts[2].replace("CVD:","")
                    rsi = parts[3].replace("RSI:","")
                    price_str = ""
                    for s in signals:
                        if s["sym"].replace("USDT","") == name:
                            price_str = " ${:.4f}".format(s["price"])
                            break
                    report.append("    ?? {:<6} {:>3}? CVD{:>6} RSI{:>3}{}".format(name, score, cvd, rsi, price_str))

        if closed:
            report.append("  ?? ????")
            for sym, reason, pnl in closed:
                em = "?" if pnl > 0 else "?"
                cn = sym.replace("USDT","")
                report.append("    {} {:<6} {} ??:{:+.1f}%".format(em, cn, reason, pnl))

        # ????
        pos_list = []
        for sym, p in list(positions.items())[:8]:
            cn = sym.replace("USDT","")
            d = "?" if p["direction"] == "long" else "?"
            pos_list.append("{}{}".format(d, cn))
        pos_str = " ".join(pos_list) if pos_list else "??"

        pnl_emoji = "??" if total_pnl >= 0 else "??"
        report.append("  ?????????????????")
        report.append("  ??: {}/{} | {} ??{:+.1f}% | ?{}?".format(len(positions), MAX_POS, pnl_emoji, total_pnl, state["trades"]))
        report.append("  [{}]".format(pos_str))
        report.append("??????????????????")

        feishu_send("\\n".join(report))
'''

new_lines = [l + "\n" for l in new_block.split("\n")]
result = lines[:178] + new_lines + lines[192:]

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.writelines(result)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
