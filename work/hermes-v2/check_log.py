import json
signals = []
with open("/home/ubuntu/hermes-v2/logs/v2_signals.jsonl") as f:
    for line in f:
        if line.strip():
            signals.append(json.loads(line))
cycles = {}
for s in signals:
    c = s["cycle"]
    if c not in cycles:
        cycles[c] = []
    cycles[c].append(s)
for c in sorted(cycles.keys()):
    print(f"Cycle {c}: {len(cycles[c])} signals")
    for s in cycles[c]:
        status = "PASS" if s["filter_passed"] else "BLOCK"
        print(f"  {status} {s['symbol']:12s} {s['direction']:5s} Score:{s['score']:+4d} ${s['price']:.4f}")
