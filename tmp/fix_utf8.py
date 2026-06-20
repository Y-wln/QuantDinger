with open("/home/ubuntu/scripts/agents/hermes_core.py") as f:
    content = f.read()

old_send = """def feishu_send(text):
    try:
        requests.post(FEISHU_WEBHOOK, json={'msg_type':'text','content':{'text':text}}, timeout=10)
    except Exception:
        pass"""

new_send = """def feishu_send(text):
    try:
        import json as _json
        body = _json.dumps({'msg_type':'text','content':{'text':text}}, ensure_ascii=False)
        requests.post(FEISHU_WEBHOOK, data=body.encode('utf-8'),
            headers={'Content-Type':'application/json; charset=utf-8'}, timeout=10)
    except Exception:
        pass"""

content = content.replace(old_send, new_send)
with open("/home/ubuntu/scripts/agents/hermes_core.py", "w") as f:
    f.write(content)

import py_compile
py_compile.compile("/home/ubuntu/scripts/agents/hermes_core.py", doraise=True)
print("feishu_send fixed - explicit UTF-8")
