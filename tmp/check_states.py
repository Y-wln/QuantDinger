import json
d = json.load(open("/home/ubuntu/scripts/agents/mercu_data/anomaly-v4.json"))
states = d.get("state_anomalies", [])
print("State anomalies:", len(states))
for s in states[:15]:
    print(" ", s.get("symbol","?"), s.get("scenario_label","?"), s.get("scenario","?"))
# Also check what scenarios exist
scenarios = set()
for s in states:
    scenarios.add(s.get("scenario","?"))
print("\nUnique scenarios:", scenarios)