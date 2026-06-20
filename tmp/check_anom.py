import json
d = json.load(open("/home/ubuntu/scripts/agents/mercu_data/anomaly-v4.json"))
data = d.get("data", [])
states = d.get("state_anomalies", [])
data_coins = set()
for item in data:
    data_coins.add(str(item.get("symbol","")).upper())
state_coins = set()
for s in states:
    state_coins.add(str(s.get("symbol","")).upper())
print("Data anomalies:", len(data), "unique coins:", len(data_coins))
print("State anomalies:", len(states), "unique coins:", len(state_coins))
print("Combined unique:", len(data_coins | state_coins))
# Show top data coins by frequency
from collections import Counter
freq = Counter()
for item in data:
    freq[str(item.get("symbol","")).upper()] += 1
print("\nTop data coins by anomaly count:")
for sym, cnt in freq.most_common(15):
    tag = " STATE" if sym in state_coins else ""
    print(" ", sym, cnt, tag)