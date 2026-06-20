import sys
sys.path.insert(0, "/home/ubuntu/hermes-v2")
from services.mercu import MerCuBridgeV3

m = MerCuBridgeV3()
print("Fresh:", m.is_fresh())
print()

signals = m.get_coin_signals()
print(f"Signals: {len(signals)}")
print()

# Show long and short separately
longs = [s for s in signals if s["direction"] == "long"]
shorts = [s for s in signals if s["direction"] == "short"]
neuts = [s for s in signals if s["direction"] == "neutral"]

print(f"Long: {len(longs)}, Short: {len(shorts)}, Neutral: {len(neuts)}")
print()

print("=== LONG ===")
for s in longs[:5]:
    print(f"  {s['symbol']:15s} score={s['score']:+3d} stage={s['stage']} ctx={s['context']}")
    print(f"    reasons: {s['reasons'][:4]}")

print()
print("=== SHORT ===")
for s in shorts[:5]:
    print(f"  {s['symbol']:15s} score={s['score']:+3d} stage={s['stage']} ctx={s['context']}")
    print(f"    reasons: {s['reasons'][:4]}")

print()
print("=== STAGE DISTRIBUTION ===")
from collections import Counter
stages = Counter(s["stage"] for s in signals)
for stage, count in stages.most_common():
    print(f"  {stage}: {count}")
