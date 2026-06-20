import json
with open("/home/ubuntu/scripts/agents/mercu_data/momentum_15m.json") as f:
    d = json.load(f)
boards = d.get("boards", {})
print("Keys:", list(boards.keys()))
for k in boards:
    items = boards[k]
    if items:
        print(k, ":", json.dumps(items[0], ensure_ascii=False)[:200])
