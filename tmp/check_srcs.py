import json
with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    d = json.load(f)
srcs = {}
for e in d:
    s = e.get("source","?")
    srcs[s] = srcs.get(s,0) + len(e["signals"])
for k,v in srcs.items():
    print(k, v)
