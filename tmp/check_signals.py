import json
with open("/home/ubuntu/hermes-v2/logs/v2_signals.jsonl") as f:
    lines = f.readlines()

# Last 10 signals
print("=== Last 10 Signals ===")
for line in lines[-10:]:
    s = json.loads(line.strip())
    d = s.get("details", {})
    cvd_keys = [k for k in d if "cvd" in k.lower() or "cv" in k.lower()]
    print(f"{s['ts']} {s['symbol']:12s} {s['direction']:5s} score={s['score']:3d} price={s['price']} filter={s.get('filter_passed','?')} cvd={cvd_keys}")

# Check for short signals
longs = sum(1 for l in lines if '"long"' in l)
shorts = sum(1 for l in lines if '"short"' in l)
print(f"\n=== Direction Balance ===")
print(f"Long: {longs}, Short: {shorts}")

# Check MerCu
mercu_count = sum(1 for l in lines if '"source": "mercu"' in l)
print(f"\nMerCu signals: {mercu_count}")

# Check sources
from collections import Counter
sources = Counter()
for line in lines:
    s = json.loads(line.strip())
    sources[s.get("source", "main")] += 1
print(f"Sources: {dict(sources)}")
