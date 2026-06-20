#!/usr/bin/env python3
"""分析纸盘交易记录 - 胜率/盈亏比/按币种/按方向"""
import json, sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/scripts/trade_log.json'
try:
    with open(path) as f:
        logs = json.load(f)
except:
    print('no trade log yet')
    sys.exit(0)

entries = [l for l in logs if l.get('type') == 'entry']
exits = [l for l in logs if l.get('type') == 'exit']

# Match entries with exits by sym+dir+time proximity
print('=' * 50)
print(f'  交易分析 | {len(exits)}笔平仓')
print('=' * 50)

wins = [e for e in exits if e.get('pnl', 0) > 0]
losses = [e for e in exits if e.get('pnl', 0) <= 0]
win_rate = len(wins) / len(exits) * 100 if exits else 0
avg_win = sum(e['pnl'] for e in wins) / len(wins) if wins else 0
avg_loss = sum(e['pnl'] for e in losses) / len(losses) if losses else 0
total_pnl = sum(e['pnl'] for e in exits)

print(f'  胜率: {win_rate:.1f}% ({len(wins)}W/{len(losses)}L)')
print(f'  平均盈利: +{avg_win:.2f}% | 平均亏损: {avg_loss:.2f}%')
print(f'  盈亏比: {abs(avg_win/avg_loss):.2f}' if avg_loss != 0 else '  盈亏比: N/A')
print(f'  累计盈亏: {total_pnl:+.2f}%')
print()

# By direction
print('  按方向:')
long_exits = [e for e in exits if e.get('dir') == 'LONG']
short_exits = [e for e in exits if e.get('dir') == 'SHORT']
for label, ex in [('做多', long_exits), ('做空', short_exits)]:
    if not ex: continue
    w = [e for e in ex if e['pnl'] > 0]
    wr = len(w)/len(ex)*100
    pnl = sum(e['pnl'] for e in ex)
    print(f'    {label}: {len(ex)}笔 胜率{wr:.0f}% 盈亏{pnl:+.1f}%')

# By coin
print('\n  按币种(>=2笔):')
by_coin = defaultdict(list)
for e in exits:
    by_coin[e['sym'].replace('USDT','')].append(e['pnl'])
for coin, pnls in sorted(by_coin.items(), key=lambda x: sum(x[1]), reverse=True):
    if len(pnls) >= 2:
        wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        print(f'    {coin:<8} {len(pnls)}笔 胜率{wr:.0f}% 累计{sum(pnls):+.1f}%')

# By entry reason
print('\n  按入场触发:')
by_reason = defaultdict(list)
for e in exits:
    reason = e.get('reason', '?')
    by_reason[reason].append(e['pnl'])
for reason, pnls in sorted(by_reason.items(), key=lambda x: sum(x[1]), reverse=True):
    wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
    print(f'    {reason:<8} {len(pnls)}笔 胜率{wr:.0f}% 累计{sum(pnls):+.1f}%')

print()
print('  最近10笔:')
for e in exits[-10:]:
    sym = e.get('sym','').replace('USDT','')
    pnl = e.get('pnl',0)
    em = '✅' if pnl > 0 else '❌'
    print(f'    {em} {sym:<6} {e.get("dir",""):<6} {pnl:+.2f}% {e.get("reason","")}')
