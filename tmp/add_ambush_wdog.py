import re
path = "/home/ubuntu/scripts/watchdog.py"
with open(path) as f:
    c = f.read()
# Add ambush after yb line
c = c.replace(
    "'yb':    'cd /home/ubuntu/scripts/agents && python3 -u yaobi_pusher.py',",
    "'yb':    'cd /home/ubuntu/scripts/agents && python3 -u yaobi_pusher.py',\n    'ambush': 'cd /home/ubuntu/scripts/agents && python3 -u ambush_scanner.py',"
)
with open(path, "w") as f:
    f.write(c)
print("Watchdog updated with ambush")
