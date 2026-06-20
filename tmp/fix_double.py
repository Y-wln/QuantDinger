with open("/home/ubuntu/scripts/agents/hermes_core.py") as f:
    content = f.read()

old_send = """def feishu_app_send(text, chat_id=None):
    try:
        if not chat_id:
            try:
                with open("/tmp/feishu_chat_id") as f:
                    chat_id = f.read().strip()
            except Exception:
                pass
        if not chat_id:
            return
        token = _get_app_token()
        if not token:
            return
        import json as _json
        body = _json.dumps({"text": text}, ensure_ascii=False)
        payload = {"receive_id": chat_id, "msg_type": "text", "content": body}
        requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=utf-8"},
            json=payload, timeout=10)
    except Exception:
        pass"""

new_send = """def feishu_app_send(text, chat_id=None):
    try:
        if not chat_id:
            try:
                with open("/tmp/feishu_chat_id") as f:
                    chat_id = f.read().strip()
            except Exception:
                pass
        if not chat_id:
            return
        token = _get_app_token()
        if not token:
            return
        import json as _json
        payload = {"receive_id": chat_id, "msg_type": "text",
            "content": _json.dumps({"text": text}, ensure_ascii=False)}
        requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            data=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=10)
    except Exception:
        pass"""

content = content.replace(old_send, new_send)
with open("/home/ubuntu/scripts/agents/hermes_core.py", "w") as f:
    f.write(content)

import py_compile
py_compile.compile("/home/ubuntu/scripts/agents/hermes_core.py", doraise=True)
print("fixed double-encoding")
