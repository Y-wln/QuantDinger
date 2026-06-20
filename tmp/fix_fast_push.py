path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add feishu push for fast warnings
old = '                if fast_warnings:\n                    print("[YaobiV17] 1m fast warnings: " + "; ".join(fast_warnings[:5]))'
new = '''                if fast_warnings:
                    print("[YaobiV17] 1m fast warnings: " + "; ".join(fast_warnings[:5]))
                    fast_msg = "\U0001f4a8 1m Fast Alert | " + datetime.now(BJT).strftime("%H:%M") + "\n" + "\n".join(fast_warnings[:3])
                    try: feishu_app_send(fast_msg, chat_id=CHAT_ID)
                    except: pass'''
content = content.replace(old, new)

# Update version: v17 -> v17.1
content = content.replace("[YaobiV17]", "[YaobiV17.1]")
content = content.replace("Yaobi Pusher v17", "Yaobi Pusher v17.1")
content = content.replace("Yaobi Scan V17", "Yaobi Scan V17.1")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fast alert push to feishu added")
