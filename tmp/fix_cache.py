import re
with open("/home/ubuntu/hermes-v2/daemon.py") as f:
    content = f.read()

# Fix kc.get calls to use long max_age during warmup
content = content.replace(
    'kc.get(sym, "4h", 300)',
    'kc.get(sym, "4h", 300, max_age=86400)'
)
content = content.replace(
    'kc.get(sym, "1h", 300)',
    'kc.get(sym, "1h", 300, max_age=3600)'
)
content = content.replace(
    'kc.get(sym, "5m", 50)',
    'kc.get(sym, "5m", 50, max_age=300)'
)
content = content.replace(
    'kc.get(sym, "15m", 30)',
    'kc.get(sym, "15m", 30, max_age=300)'
)

with open("/home/ubuntu/hermes-v2/daemon.py", "w") as f:
    f.write(content)
print("Fixed daemon.py cache expiry")
