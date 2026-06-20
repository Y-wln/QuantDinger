import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

# Fix feishu_callback.py send_msg and send_card
with open('/home/ubuntu/scripts/agents/feishu_callback.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix send_msg - add ensure_ascii=False
old = "'msg_type':'text','content':json.dumps({'text':text})"
new = "'msg_type':'text','content':json.dumps({'text':text}, ensure_ascii=False)"
if old in content:
    content = content.replace(old, new)
    print('send_msg: fixed')
else:
    print('send_msg: NOT FOUND, searching...')
    # Try broader search
    if "json.dumps({'text':text})" in content:
        content = content.replace("json.dumps({'text':text})", "json.dumps({'text':text}, ensure_ascii=False)")
        print('send_msg: fixed (alt)')

# Fix send_card - add ensure_ascii=False
old2 = "'msg_type':'interactive','content':json.dumps(card)"
new2 = "'msg_type':'interactive','content':json.dumps(card, ensure_ascii=False)"
if old2 in content:
    content = content.replace(old2, new2)
    print('send_card: fixed')
else:
    if "json.dumps(card)" in content:
        content = content.replace("json.dumps(card)", "json.dumps(card, ensure_ascii=False)")
        print('send_card: fixed (alt)')

with open('/home/ubuntu/scripts/agents/feishu_callback.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify compile
import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/feishu_callback.py', doraise=True)
print('feishu_callback.py: compiles OK')
