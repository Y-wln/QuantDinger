# Update signal_tracker.py to support source parameter
path = "/home/ubuntu/scripts/agents/signal_tracker.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Update track_signals function signature
old = "def track_signals(signals):"
new = "def track_signals(signals, source=\"yaobi\"):"
content = content.replace(old, new)

# Add source to entry
old_entry = '"ts": time.time(),'
new_entry = '"ts": time.time(),\n        "source": source,'
content = content.replace(old_entry, new_entry)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Tracker updated with source support")
