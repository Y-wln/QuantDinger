path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old = 'fast_msg = "\U0001f4a8 1m Fast Alert | " + datetime.now(BJT).strftime("%H:%M") + "\n" + "\n".join(fast_warnings[:3])'
new = 'fast_msg = "\U0001f4a8 1m Fast Alert | " + datetime.now(BJT).strftime("%H:%M") + chr(10) + chr(10).join(fast_warnings[:3])'
c = c.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Fixed")
