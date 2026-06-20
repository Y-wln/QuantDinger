import json, sys, os, time
from collections import defaultdict

sys.path.insert(0, "/home/ubuntu/hermes-v2")

# Read mercu signal log
log_file = "/home/ubuntu/hermes-v2/logs/v2_mercu.jsonl"
if not os.path.exists(log_file):
    print("NO mercu log file")
    sys.exit(1)

signals = []
with open(log_file) as f:
    for line in f:
        if line.strip():
            signals.append(json.loads(line.strip()))

print(f"Total MerCu signals in log: {len(signals)}")

# Group by symbol + direction
from collections import Counter
dirs = Counter(s["direction"] for s in signals)
print(f"Direction: long={dirs.get('long',0)}, short={dirs.get('short',0)}")

# Check time range
ts_list = sorted(set(s["ts"] for s in signals))
print(f"Time range: {ts_list[0]} -> {ts_list[-1]}")
print(f"Unique timestamps: {len(ts_list)}")

# Latest signals
print("\n=== Latest 10 signals ===")
for s in signals[-10:]:
    print(f"  {s['ts']} {s['direction']:5s} {s['symbol']:15s} score={s['score']:+3d} {s.get('reasons','?')}")

# Now test accuracy: for each signal, check price 5min, 15min, 30min later
print("\n=== Accuracy Test (using Binance klines) ===")

from core.http_client import HTTPClient
from core.exchange import ExchangeAPI

http = HTTPClient()
ex = ExchangeAPI(http)

results = {"long": {"win": 0, "loss": 0, "total": 0},
           "short": {"win": 0, "loss": 0, "total": 0}}

# Only test unique (symbol, direction, ts) combinations
tested = set()
for s in signals[-30:]:  # Test last 30 unique signals
    key = (s["symbol"], s["direction"], s["ts"])
    if key in tested:
        continue
    tested.add(key)

    try:
        # Parse timestamp
        from datetime import datetime, timezone, timedelta
        bjt = timezone(timedelta(hours=8))
        sig_time = datetime.strptime(s["ts"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=bjt)

        # Get klines around signal time
        klines = ex.klines(s["symbol"], "1m", 60)
        if not klines or len(klines) < 30:
            continue

        # Find closest candle to signal time
        sig_price = None
        for k in klines:
            k_ts = datetime.fromtimestamp(int(k["ts"]) / 1000, tz=timezone.utc)
            if abs((k_ts - sig_time).total_seconds()) < 120:
                sig_price = float(k["c"])
                break

        if sig_price is None:
            sig_price = float(klines[-30]["c"])

        # Check price 15 min and 30 min later
        for offset_min, label in [(15, "15min"), (30, "30min")]:
            target_time = sig_time + timedelta(minutes=offset_min)
            target_price = None
            for k in klines:
                k_ts = datetime.fromtimestamp(int(k["ts"]) / 1000, tz=timezone.utc)
                if abs((k_ts - target_time).total_seconds()) < 120:
                    target_price = float(k["c"])
                    break
            if target_price is None:
                target_price = float(klines[-1]["c"])  # use last available

            pct = (target_price - sig_price) / sig_price * 100
            if s["direction"] == "long" and pct > 0.1:
                results["long"]["win"] += 1
            elif s["direction"] == "long" and pct < -0.1:
                results["long"]["loss"] += 1
            elif s["direction"] == "short" and pct < -0.1:
                results["short"]["win"] += 1
            elif s["direction"] == "short" and pct > 0.1:
                results["short"]["loss"] += 1

            results[s["direction"]]["total"] += 1

    except Exception as e:
        print(f"  Error: {s['symbol']} {e}")
        continue

print("\n=== Results ===")
for d in ("long", "short"):
    r = results[d]
    if r["total"] > 0:
        acc = 100 * r["win"] / r["total"]
        print(f"  {d:5s}: {r['win']}W/{r['loss']}L/{r['total']}total = {acc:.0f}% accuracy")
    else:
        print(f"  {d:5s}: no signals tested")
