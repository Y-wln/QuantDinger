import re

path = '/home/ubuntu/hermes-v2/daemon.py'
with open(path, encoding='utf-8-sig') as f:
    content = f.read()

# 1. Add cooldown state init
old_init = '        try:\n            mercu_signals = mercu.get_coin_signals()'
new_init = '''        if \"mercu_last_key\" not in dir():
            mercu_last_key = \"\"
            mercu_last_ts = 0
        mercu_now_bucket = int(time.time() / 120) * 120
        
        try:
            mercu_signals = mercu.get_coin_signals()'''
content = content.replace(old_init, new_init)

# 2. Add cooldown check before msg_lines
old_msg = 'msg_lines = [\"📡 MerCu | \" + ts[-5:], \"━━━━━━━━━━━━\"]'
new_msg = '''long_key = \",\".join(\"{}={}\".format(s[\"symbol\"],s[\"score\"]) for s in mercu_long)
                short_key = \",\".join(\"{}={}\".format(s[\"symbol\"],s[\"score\"]) for s in mercu_short)
                mercu_cur_key = long_key + \"|\" + short_key
                mercu_should_push = (mercu_cur_key != mercu_last_key or mercu_now_bucket - mercu_last_ts >= 600)
                if mercu_should_push:
                    mercu_last_key = mercu_cur_key
                    mercu_last_ts = mercu_now_bucket
                msg_lines = [\"📡 MerCu | \" + ts[-5:], \"━━━━━━━━━━━━\"]'''
content = content.replace(old_msg, new_msg)

# 3. Wrap push in cooldown guard
old_push = '                # Push to Feishu\n                try:\n                    import urllib.request\n                    payload = json.dumps({\"msg_type\": \"text\", \"content\": {\"text\": mer_msg}}).encode()\n                    req = urllib.request.Request(alerts.webhook, data=payload,\n                        headers={\"Content-Type\": \"application/json\"})\n                    urllib.request.urlopen(req, timeout=5)\n                    with open(os.path.join(alerts.log_dir, \"alerts_{}.log\".format(time.strftime(\"%Y%m%d\"))), \"a\") as f:\n                        f.write(\"[{}] [MERCu] pushed {}L/{}S\\n\".format(ts, len(mercu_long), len(mercu_short)))\n                except Exception:\n                    pass'
new_push = '                # Push to Feishu (cooldown: 10min or score change)\n                if mercu_should_push:\n                    try:\n                        import urllib.request\n                        payload = json.dumps({\"msg_type\": \"text\", \"content\": {\"text\": mer_msg}}).encode()\n                        req = urllib.request.Request(alerts.webhook, data=payload,\n                            headers={\"Content-Type\": \"application/json\"})\n                        urllib.request.urlopen(req, timeout=5)\n                        with open(os.path.join(alerts.log_dir, \"alerts_{}.log\".format(time.strftime(\"%Y%m%d\"))), \"a\") as f:\n                            f.write(\"[{}] [MERCu] pushed {}L/{}S\\n\".format(ts, len(mercu_long), len(mercu_short)))\n                    except Exception:\n                        pass'
assert old_push in content, 'Push block not found!'
content = content.replace(old_push, new_push)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Cooldown patch applied OK')
