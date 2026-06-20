import json
with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    d = json.load(f)

yaobi = [e for e in d if e.get("source") == "yaobi"]
mercu = [e for e in d if e.get("source") == "mercu"]
print("Yaobi:", sum(len(e["signals"]) for e in yaobi), "signals")
print("MerCu:", sum(len(e["signals"]) for e in mercu), "signals")
print()
for e in d:
    src = e.get("source", "?")
    for s in e["signals"]:
        print(e["time"], src.ljust(6), s["sym"].ljust(6), s["dir"].ljust(5), s["price"])
