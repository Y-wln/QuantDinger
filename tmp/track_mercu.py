# Add signal tracking to mercu_signals.py
path = "/home/ubuntu/scripts/agents/mercu_signals.py"
with open(path, "r", encoding="utf-8-sig") as f:
    content = f.read()

# Add import
old_import = "from hermes_core import feishu_app_send, fetch_price"
new_import = "from hermes_core import feishu_app_send, fetch_price\nfrom signal_tracker import track_signals"
content = content.replace(old_import, new_import)

# Add track call after feishu push
old_push = 'feishu_app_send(chr(10).join(lines), chat_id=CHAT)'
new_push = 'track_signals(signals, source="mercu")\n            feishu_app_send(chr(10).join(lines), chat_id=CHAT)'
content = content.replace(old_push, new_push)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("MerCu tracker added")
