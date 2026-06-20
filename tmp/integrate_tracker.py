path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add import
old_import = "from cross_validate import write_signals, get_badge"
new_import = "from cross_validate import write_signals, get_badge\nfrom signal_tracker import track_signals"
content = content.replace(old_import, new_import)

# Add track_signals call after write_signals
old_push = "            write_signals(\"yaobi\", cross_sigs)\n            feishu_app_send"
new_push = "            write_signals(\"yaobi\", cross_sigs)\n            track_signals(signals)\n            feishu_app_send"
content = content.replace(old_push, new_push)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Tracker integrated")
