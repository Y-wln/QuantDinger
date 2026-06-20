import re

path = '/home/ubuntu/hermes-v2/daemon.py'
with open(path, encoding='utf-8-sig') as f:
    content = f.read()

# Add main cooldown state init
old = '        # MerCu push cooldown tracker'
new = '''        # Main push cooldown tracker
        if \"main_last_key\" not in dir():
            main_last_key = \"\"
            main_last_ts = 0
        # MerCu push cooldown tracker'''
content = content.replace(old, new)

# Find the main signal logging section and add cooldown before print
# The main signals loop has print("  [{}] MAIN ...") for each signal
# We want to skip Feishu push but keep logging. Main doesn't push to Feishu currently.
# So MAIN cooldown is just for deduplication in the pipeline/log
# Actually MAIN only logs and tracks, so cooldown isn't needed for push.
# The issue is MerCu that pushes to Feishu every cycle.

print('MAIN does not push to Feishu - no cooldown needed')
print('MerCu cooldown already applied')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
