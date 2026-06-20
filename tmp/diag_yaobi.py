import sys, json
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_state.json') as f:
    s = json.load(f)

# Check per-coin params used
try:
    with open('/home/ubuntu/scripts/agents/per_coin_params.json') as f:
        pcp = json.load(f)
except:
    pcp = {}

pos = s.get('positions', {})
print("=== ?????? ===")
print(f"??: {s.get('trades',0)}? | PnL: {s.get('pnl',0):+.1f}%")
print()

for sym, p in pos.items():
    d = p.get('direction','?')
    entry = p.get('entry',0)
    sl = p.get('sl',0)
    tp = p.get('tp',0)
    # Check if this coin has custom params
    cp = pcp.get(sym, {})
    fast = cp.get('fast', False)
    print(f"{sym:15s} {d:6s} @{entry:<10} SL:{sl:<10} TP:{tp:<10} fast={fast}")

print()
print("=== ??v11???? ===")
print("????: CVD(1h+15m) + RSI + ?? + ???? + 5m? + OI + Taker + LSR + ??? + 1mCVD + ??")
print()
print("????:")
print("1.??????(??5m??5-10%), SL 3-5%?????")
print("2.625??????????,?????")
print("3.???????'????'??(?????)")
print("4.??/?????????????")
