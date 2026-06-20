with open("/home/ubuntu/scripts/yaobi_v8.py") as f:
    lines = f.readlines()

# Find boundaries
alert_start = -1
msg_start = -1
msg_end = -1

for i, line in enumerate(lines):
    if "alerts = []" in line and "new_trades" not in line and i > 120:
        alert_start = i
    if i > 170 and "????" in line:
        msg_start = i
    if msg_start > 0 and "feishu_send" in line and i > msg_start:
        msg_end = i + 1
        break

print(f"alert_start={alert_start+1} msg_start={msg_start+1} msg_end={msg_end}")

if alert_start < 0 or msg_start < 0 or msg_end < 0:
    print("FAIL")
else:
    new_section = '''    alerts = []
    new_trades = 0

    for s in new_signals[:5]:
        sym = s['sym']
        if s['score'] >= 12:
            alerts.append("LONG|" + sym + "|" + str(s["score"]) + "|" + str(round(s["cvd"],1)) + "|" + str(int(s["rsi"])) + "|" + str(round(s["price"],4)))
            positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']*(1-SL_PCT),
                'tp':s['price']*(1+TP_PCT),'time':now.isoformat(),'reasons':s['reasons']}
            new_trades += 1
        elif s['score'] <= -12:
            alerts.append("SHORT|" + sym + "|" + str(s["score"]) + "|" + str(round(s["cvd"],1)) + "|" + str(int(s["rsi"])) + "|" + str(round(s["price"],4)))
            positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']*(1+SL_PCT),
                'tp':s['price']*(1-TP_PCT),'time':now.isoformat(),'reasons':s['reasons']}
            new_trades += 1

    # ????/??
    closed = []
    for sym, p in list(positions.items()):
        price = 0
        try:
            data = proxy_mgr.fetch_json(BINANCE+'/api/v3/ticker/price?symbol='+sym, 8)
            price = float(data.get('price', 0))
        except: continue
        if not price: continue
        if p['direction'] == 'long':
            if price <= p['sl']:
                pnl = (price-p['entry'])/p['entry']*100
                closed.append((sym, '??', pnl))
                positions.pop(sym)
            elif price >= p['tp']:
                pnl = (price-p['entry'])/p['entry']*100
                closed.append((sym, '??', pnl))
                positions.pop(sym)
        else:
            if price >= p['sl']:
                pnl = (p['entry']-price)/p['entry']*100
                closed.append((sym, '??', pnl))
                positions.pop(sym)
            elif price <= p['tp']:
                pnl = (p['entry']-price)/p['entry']*100
                closed.append((sym, '??', pnl))
                positions.pop(sym)

    # ?8??????
    while len(positions) > MAX_POS:
        positions.pop(list(positions.keys())[0])

    state['positions'] = positions
    state['trades'] = state.get('trades',0) + new_trades + len(closed)
    total_pnl = state.get('pnl', 0)
    for _, _, pnl in closed: total_pnl += pnl
    state['pnl'] = total_pnl

    # ??????????
    if alerts or closed or new_trades:
        t = now.strftime("%m/%d %H:%M")
        report = []
        report.append("??????????????????")
        report.append("  ?? ???? | " + t)
        report.append("??????????????????")

        longs = [a for a in alerts if a.startswith("LONG|")]
        shorts = [a for a in alerts if a.startswith("SHORT|")]

        if longs:
            report.append("  ?? ????")
            for a in longs[:5]:
                parts = a.split("|")
                if len(parts) >= 6:
                    _, nm, sc, cv, rs, pr = parts
                    cn = nm.replace("USDT","")
                    report.append("    ?? {:<6} {:>3}? CVD{:>6}% RSI{:>3} ${}".format(cn, sc, cv, rs, pr))

        if shorts:
            report.append("  ?? ????")
            for a in shorts[:5]:
                parts = a.split("|")
                if len(parts) >= 6:
                    _, nm, sc, cv, rs, pr = parts
                    cn = nm.replace("USDT","")
                    report.append("    ?? {:<6} {:>3}? CVD{:>6}% RSI{:>3} ${}".format(cn, sc, cv, rs, pr))

        if closed:
            report.append("  ?? ????")
            for sym, reason, pnl in closed:
                em = "?" if pnl > 0 else "?"
                cn = sym.replace("USDT","")
                report.append("    {} {:<6} {} ??:{:+.1f}%".format(em, cn, reason, pnl))

        pos_list = []
        for sym, p in list(positions.items()):
            cn = sym.replace("USDT","")
            d = "?" if p["direction"] == "long" else "?"
            pos_list.append("{}{}".format(d, cn))
        pos_str = " ".join(pos_list[:8]) if pos_list else "??"

        pnl_emoji = "??" if total_pnl >= 0 else "??"
        report.append("  ?????????????????")
        report.append("  ??: {}/{} | {} ??{:+.1f}% | ?{}?".format(len(positions), MAX_POS, pnl_emoji, total_pnl, state["trades"]))
        report.append("  [{}]".format(pos_str))
        report.append("??????????????????")

        feishu_send(chr(10).join(report))

    save_state(state)
'''

    new_lines = [l + "\n" for l in new_section.split("\n")]
    result = lines[:alert_start] + new_lines + lines[msg_end:]

    with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
        f.writelines(result)

    import py_compile
    try:
        py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
        print("COMPILE OK")
    except py_compile.PyCompileError as e:
        print("ERROR: " + str(e))
