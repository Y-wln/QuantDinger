with open("/home/ubuntu/scripts/yaobi_v8.py") as f:
    content = f.read()

# Replace the message building section
old_msgs = """    # ????
    msgs = []
    if alerts:
        msgs.append('?? ???? | ' + now.strftime('%m/%d %H:%M'))
        msgs.extend(alerts[:5])
    if closed:
        msgs.append('?? ??')
        for sym, reason, pnl in closed:
            msgs.append(f"  {'?' if pnl>0 else '?'} {sym.replace('USDT','')} {reason} PnL:{pnl:+.2f}%")
    if new_trades or closed:
        msgs.append(f'??:{len(positions)}/{MAX_POS} | PnL:{total_pnl:+.1f}% | ??:{state["trades"]}')
    if msgs:
        feishu_send('\n'.join(msgs))"""

new_msgs = """    # ??????????
    if alerts or closed or new_trades:
        lines = []
        t = now.strftime('%m/%d %H:%M')
        lines.append(f'??????????????????')
        lines.append(f'  ?? ???? | {t}')
        lines.append(f'??????????????????')

        if alerts:
            # Group by direction
            longs = [a for a in alerts if '??' in a]
            shorts = [a for a in alerts if '??' in a]

            if longs:
                lines.append('')
                lines.append('  ?? ????')
                for a in longs[:5]:
                    # Parse: "?? CHZ LONG | 20? | CVD:24.8% RSI:50"
                    parts = a.replace('?? ','').split(' | ')
                    name = parts[0].replace(' LONG','')
                    score = parts[1].replace('?','')
                    cvd = parts[2].replace('CVD:','')
                    rsi = parts[3].replace('RSI:','')
                    # Get price from signals
                    price_str = ''
                    for s in signals:
                        if s['sym'].replace('USDT','') == name:
                            price_str = f"${s['price']:.4f}"
                            break
                    lines.append(f'    ?? {name:<6} {score:>3}? CVD{cvd:>6} RSI{rsi:>3} {price_str}')

            if shorts:
                lines.append('')
                lines.append('  ?? ????')
                for a in shorts[:5]:
                    parts = a.replace('?? ','').split(' | ')
                    name = parts[0].replace(' SHORT','')
                    score = parts[1].replace('?','')
                    cvd = parts[2].replace('CVD:','')
                    rsi = parts[3].replace('RSI:','')
                    price_str = ''
                    for s in signals:
                        if s['sym'].replace('USDT','') == name:
                            price_str = f"${s['price']:.4f}"
                            break
                    lines.append(f'    ?? {name:<6} {score:>3}? CVD{cvd:>6} RSI{rsi:>3} {price_str}')

        if closed:
            lines.append('')
            lines.append('  ?? ????')
            for sym, reason, pnl in closed:
                em = '?' if pnl > 0 else '?'
                cn = sym.replace('USDT','')
                lines.append(f'    {em} {cn:<6} {reason} ??:{pnl:+.1f}%')

        lines.append('')
        lines.append(f'  ?????????????????')
        # Current positions summary
        pos_summary = []
        for sym, p in list(positions.items())[:8]:
            cn = sym.replace('USDT','')
            d = '?' if p['direction'] == 'long' else '?'
            pos_summary.append(f'{d}{cn}')
        pos_str = ' '.join(pos_summary) if pos_summary else '??'

        pnl_emoji = '??' if total_pnl >= 0 else '??'
        lines.append(f'  ??: {len(positions)}/{MAX_POS} | {pnl_emoji} ??{total_pnl:+.1f}% | ?{state["trades"]}?')
        lines.append(f'  [{pos_str}]')
        lines.append(f'??????????????????')

        feishu_send('\n'.join(lines))"""

if old_msgs in content:
    content = content.replace(old_msgs, new_msgs)
    print("Report format updated")
else:
    print("PATTERN FAIL")

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
