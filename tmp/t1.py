import json
d = json.load(open("/home/ubuntu/scripts/agents/hermes_state.json"))
print(f"orch??: {len(d.get('positions',{}))}")
