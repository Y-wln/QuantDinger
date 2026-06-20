path = "/home/ubuntu/scripts/agents/ambush_scanner.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Add import
c = c.replace("from hermes_core import", "from signal_tracker import track_signals\nfrom hermes_core import")

# Add tracking after feishu push  
old = "feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)\n            print(\"[AmbushV3]"
new = """# Convert to tracker format and log
            ambush_sigs = [{"sym": s[0].replace("USDT",""), "dir": s[1], "price": s[3], "score": s[4], "reasons": ["OB:" + str(s[2]) + "%", "CVD:" + str(s[5])]} for s in signals]
            track_signals(ambush_sigs, source="ambush")
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
            print("[AmbushV3]"""
c = c.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Ambush tracker added")
