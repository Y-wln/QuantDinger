import py_compile, os

# ====== Fix sentinel (yaobi_sentinel.py) ======
with open('/home/ubuntu/scripts/yaobi_sentinel.py', 'r') as f:
    content = f.read()

# Change cooldown 300->600
content = content.replace('COOLDOWN = 300', 'COOLDOWN = 600')

# Change messages to Chinese
content = content.replace(
    "lines = [emoji + ' ' + name + ' alert ' + now + ' | $' + str(price) + ' | ' + dir_cn + ' | 24h:' + str(round(chg,1)) + '%']",
    "lines = [emoji + ' ' + name + ' ' + dir_cn + ' | $' + str(price) + ' | 24h:' + str(round(chg,1)) + '%']")

content = content.replace(
    "            emoji = 'LONG' if direction == 'long' else 'SHORT'\n            dir_cn = 'L' if direction == 'long' else 'S'",
    "            emoji = 'L' if direction == 'long' else 'S'\n            dir_cn = chr(22823) + chr(22810) if direction == 'long' else chr(22823) + chr(31354)")

# Better: use actual Chinese text
old_emoji = """            emoji = 'L' if direction == 'long' else 'S'
            dir_cn = chr(22823) + chr(22810) if direction == 'long' else chr(22823) + chr(31354)"""
new_emoji = """            emoji = '\U0001f7e2' if direction == 'long' else '\U0001f534'
            dir_cn = '\u505a\u591a' if direction == 'long' else '\u505a\u7a7a'"""
content = content.replace(old_emoji, new_emoji)

# Fix startup message
content = content.replace(
    "feishu_send('Sentinel online | 10s scan | top10 active coins')",
    "feishu_send('\U0001f6e1\ufe0f \u5996\u5e01\u54e8\u5175\u4e0a\u7ebf | 10s\u626b\u63cf | TOP10\u5f02\u52a8\u5e01')")

with open('/home/ubuntu/scripts/yaobi_sentinel.py', 'w') as f:
    f.write(content)

for d in ['/home/ubuntu/scripts/__pycache__', '/home/ubuntu/scripts/agents/__pycache__']:
    if os.path.exists(d):
        for f in os.listdir(d):
            if 'yaobi_sentinel' in f:
                os.remove(os.path.join(d, f))

py_compile.compile('/home/ubuntu/scripts/yaobi_sentinel.py', doraise=True)
print('sentinel: fixed')

# ====== Fix signal pusher ======
with open('/home/ubuntu/scripts/agents/signal_pusher.py', 'r') as f:
    content = f.read()

content = content.replace('COOLDOWN = 300', 'COOLDOWN = 600')

old_pusher_msg = """            d = 'LONG' if score > 0 else 'SHORT'
            ck = sym + '_' + d"""
new_pusher_msg = """            d = 'long' if score > 0 else 'short'
            ck = sym + '_' + d"""
content = content.replace(old_pusher_msg, new_pusher_msg)

# Chinese launch message
old_launch = """            lines = [d + ' ' + name + ' launch ' + now + ' score=' + str(score)]"""
new_launch = """            dir_cn = '\u505a\u591a' if score > 0 else '\u505a\u7a7a'
            lines = [name + ' \u542f\u52a8\u4fe1\u53f7 | ' + now + ' | ' + dir_cn + ' | \u5206:' + str(score)]"""
content = content.replace(old_launch, new_launch)

content = content.replace(
    "feishu_send('Signal Pusher online | 12 coins | 15s scan | min_score=' + str(MIN_SCORE))",
    "feishu_send('\U0001f514 \u4e3b\u6d41\u5e01\u542f\u52a8\u63a8\u9001\u4e0a\u7ebf | 12\u5e01 | 15s')")

with open('/home/ubuntu/scripts/agents/signal_pusher.py', 'w') as f:
    f.write(content)

py_compile.compile('/home/ubuntu/scripts/agents/signal_pusher.py', doraise=True)
print('pusher: fixed')
