#!/usr/bin/env python3
"""Quick accuracy verification for V2 signals."""
import json, os, sys, time
from collections import defaultdict
from datetime import datetime, timedelta

LOG_FILE = os.path.expanduser("~/hermes-v2/logs/v2_signals.jsonl")
DECISIONS_DIR = os.path.expanduser("~/hermes-v2/logs/decisions")

# 1. Signal summary
def analyze_signals():
    signals = []
    with open(LOG_FILE) as f:
        for line in f:
            if line.strip():
                signals.append(json.loads(line))
    
    print(f"=== V2 Signal Summary ===")
    print(f"Total signals: {len(signals)}")
    
    # Time range
    first_ts = min(s["ts"] for s in signals)
    last_ts = max(s["ts"] for s in signals)
    print(f"Time range: {first_ts} -> {last_ts}")
    
    # Per direction
    direction_counts = defaultdict(int)
    for s in signals:
        direction_counts[s["direction"]] += 1
    print(f"Direction: long={direction_counts['long']}, short={direction_counts['short']}")
    
    # Per coin top 10
    coin_counts = defaultdict(int)
    for s in signals:
        coin_counts[s["symbol"]] += 1
    print(f"\nTop coins by signal count:")
    for coin, count in sorted(coin_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {coin}: {count} signals")
    
    # Filter pass rate
    passed = sum(1 for s in signals if s.get("filter_passed"))
    print(f"\nFilter pass rate: {passed}/{len(signals)} ({100*passed/max(1,len(signals)):.1f}%)")
    
    # DAG consensus rate (newer signals have dag field)
    dag_present = [s for s in signals if "dag" in s]
    if dag_present:
        dag_passed = sum(1 for s in dag_present if "" in s.get("dag", "") and "" not in s.get("dag", ""))
        print(f"DAG present in: {len(dag_present)} signals")
    
    # 2. Leading indicator stats
    indicator_stats = defaultdict(lambda: {"total": 0, "leading": 0})
    for s in signals:
        details = s.get("details", {})
        leading = s.get("leading", [])
        leading_set = set(leading)
        for key, val in details.items():
            indicator_stats[key]["total"] += 1
            if val in leading_set:
                indicator_stats[key]["leading"] += 1
    
    print(f"\n=== Leading Indicator Performance ===")
    print(f"{'Indicator':<25} {'Total':>6} {'Leading':>8} {'Rate':>7}")
    print("-" * 50)
    for ind, stats in sorted(indicator_stats.items(), key=lambda x: -x[1]["leading"]):
        rate = 100 * stats["leading"] / max(1, stats["total"])
        bar = "?" * int(rate / 5)
        print(f"  {ind:<23} {stats['total']:>6} {stats['leading']:>8} {rate:>6.1f}% {bar}")
    
    # 3. Avg score per coin (last 50 signals)
    recent_signals = signals[-50:]
    coin_scores = defaultdict(list)
    for s in recent_signals:
        coin_scores[s["symbol"]].append(s["score"])
    
    print(f"\n=== Recent Avg Scores (last 50 signals) ===")
    for coin, scores in sorted(coin_scores.items(), key=lambda x: -sum(x[1])/len(x[1])):
        avg = sum(scores) / len(scores)
        print(f"  {coin}: avg={avg:.1f} (n={len(scores)})")
    
    # 4. Signal frequency
    if len(signals) >= 2:
        t1 = datetime.strptime(signals[0]["ts"], "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(signals[-1]["ts"], "%Y-%m-%d %H:%M:%S")
        duration_min = (t2 - t1).total_seconds() / 60
        freq = len(signals) / max(1, duration_min) * 60
        print(f"\n=== Frequency ===")
        print(f"  Duration: {duration_min:.0f} min")
        print(f"  Signals/hour: {freq:.1f}")
    
    # 5. Check decision log depth
    print(f"\n=== Decision Logs ===")
    total_entries = 0
    for fname in os.listdir(DECISIONS_DIR):
        if fname.endswith(".jsonl"):
            with open(os.path.join(DECISIONS_DIR, fname)) as f:
                count = sum(1 for _ in f)
            total_entries += count
            if count > 500:
                print(f"  {fname}: {count} entries [BIG]")
    print(f"  Total decision entries: {total_entries}")

    # 6. Check MerCu data freshness
    mercu_present = [s for s in signals if s.get("source") == "mercu"]
    print(f"\n=== MerCu Integration ===")
    print(f"  MerCu signals: {len(mercu_present)}/{len(signals)}")
    if mercu_present:
        latest_mercu = max(s["ts"] for s in mercu_present)
        print(f"  Latest MerCu signal: {latest_mercu}")

    return signals

if __name__ == "__main__":
    analyze_signals()
