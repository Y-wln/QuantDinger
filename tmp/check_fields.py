import json
with open("/home/ubuntu/scripts/agents/mercu_data/anomaly-v4_100.json") as f:
    data = json.load(f)
items = data.get("data", [])
print(f"Total items: {len(items)}")

# Show all fields
all_keys = set()
for item in items:
    for k in item.keys():
        all_keys.add(k)
print("Fields:", sorted(all_keys))

# Show first 5 items fully
for item in items[:5]:
    print(json.dumps(item, ensure_ascii=False, indent=2))
    print("---")
