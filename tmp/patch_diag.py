# -*- coding: utf-8 -*-
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# Add scan stats tracking
old_init = "scan_count = 0"
new_init = "scan_count = 0\nmax_chg_seen = {}  # track max price change per coin for diagnostics"
code = code.replace(old_init, new_init)

# Track max changes in scan
old_track = "            if len(hist) < 8:\n                continue"
new_track = "            if len(hist) < 8:\n                continue\n\n            # Diagnostic: track max change seen\n            cn = sym.replace('USDT','')\n            if cn not in max_chg_seen or abs(chg_pct) > max_chg_seen.get(cn, 0):\n                max_chg_seen[cn] = abs(chg_pct)"
code = code.replace(old_track, new_track)

# Enhanced heartbeat with top movers
old_hb = "            pos_info = ' '.join([f\"{p['direction'][0]}{k.replace('USDT','')}\" for k,p in positions.items()]) or '空仓'\n            print(f'[{datetime.now(BJT).strftime(\"%H:%M:%S\")}] heartbeat:{scan_count} pos:{len(positions)} [{pos_info}] pnl:{total_pnl:+.2f}%')"
new_hb = "            pos_info = ' '.join([f\"{p['direction'][0]}{k.replace('USDT','')}\" for k,p in positions.items()]) or '空仓'\n            top_movers = sorted(max_chg_seen.items(), key=lambda x: x[1], reverse=True)[:3]\n            mover_str = ' | '.join([f\"{c}:{v:.1f}%\" for c,v in top_movers]) if top_movers else 'none'\n            print(f'[{datetime.now(BJT).strftime(\"%H:%M:%S\")}] hb:{scan_count} pos:{len(positions)} [{pos_info}] pnl:{total_pnl:+.2f}% top:{mover_str}')\n            max_chg_seen.clear()"
code = code.replace(old_hb, new_hb)

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('patched diag')
