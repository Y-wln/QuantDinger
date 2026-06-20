import json
d = json.load(open("/home/ubuntu/hermes-v2/logs/pipeline_tracker.json"))
print("pipelines:", len(d["pipelines"]), "active:", len(d.get("active", {})))
if d["pipelines"]:
    for p in d["pipelines"][-5:]:
        print("  ", p.get("symbol"), p.get("status"), p.get("direction"), p.get("signal_score"), p.get("early_price"))
