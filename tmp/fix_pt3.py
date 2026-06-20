import re

path = "/home/ubuntu/hermes-v2/services/pipeline_tracker.py"
with open(path, encoding="utf-8-sig") as f:
    content = f.read()

# === Fix 1: Insert dedup logic after "d = _load()" in signal_confirmed ===
insert_code = '''    if pid is None:
        pid = "%s_%s_%d" % (symbol.replace("USDT",""), direction, int(time.time()/120)*120)
    for ep, epipe in list(d.get("active",{}).items()):
        if epipe.get("symbol") == symbol.replace("USDT","") and epipe.get("direction") == direction:
            if not epipe.get("signal_time"):
                epipe["status"] = "active"
                epipe["signal_time"] = time.time()
                epipe["signal_time_str"] = datetime.now(BJT).strftime("%m/%d %H:%M:%S")
                epipe["signal_price"] = price
                epipe["signal_score"] = score
                epipe["signal_source"] = source
                epipe["signal_indicators"] = indicators or {}
            _save(d)
            return pid
'''

old_marker = "    d = _load()\n    \n    # Find or create pipeline"
new_marker = "    d = _load()\n" + insert_code + "    \n    # Find or create pipeline"
assert old_marker in content, "Marker not found!"
content = content.replace(old_marker, new_marker, 1)

# === Fix 2: Limit pipelines ===
content = content.replace("len(d['pipelines']) > 1000", "len(d['pipelines']) > 500")
content = content.replace("d['pipelines'][-1000:]", "d['pipelines'][-500:]")

# === Fix 3: Cap active snapshots ===
old_for = "for pid, pipe in list(d['active'].items()):\n        if pipe.get('settled'):"
new_for = "for pid, pipe in list(d['active'].items())[:50]:\n        if pipe.get('settled'):"
content = content.replace(old_for, new_for)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("pipeline_tracker.py fixed successfully")
