import json
from collections import Counter
with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    data = json.load(f)
sources = Counter()
all_sigs = []
for entry in data:
    src = entry["source"]
    sources[src] += len(entry["signals"])
    for s in entry["signals"]:
        all_sigs.append({"src": src, "sym": s["sym"], "dir": s["dir"], "score": s.get("score",0)})
print("=== Signal counts ===")
for src, cnt in sources.most_common():
    print("  {}: {}".format(src, cnt))
print("Total entries: {}, signals: {}".format(len(data), len(all_sigs)))
print("Latest 20:")
for s in all_sigs[-20:]:
    print("  [{}] {} {} score={}".format(s["src"], s["dir"], s["sym"], s["score"]))