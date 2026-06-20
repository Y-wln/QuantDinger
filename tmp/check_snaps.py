import json
d = json.load(open("/home/ubuntu/hermes-v2/logs/pipeline_tracker.json"))
for p in d["pipelines"]:
    snaps = p.get("snapshots", [])
    print(p["symbol"], p["status"], p["direction"], "snaps:", len(snaps), "mfe:", p.get("mfe_pct",0), "mae:", p.get("mae_pct",0))
