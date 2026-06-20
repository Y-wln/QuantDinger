# Add feishu_app_send to hermes_core.py
with open("/home/ubuntu/scripts/agents/hermes_core.py") as f:
    content = f.read()

# Add after the feishu_card function
old_card_end = """        requests.post(FEISHU_WEBHOOK, json=card, timeout=10)
    except Exception:
        pass"""

new_block = """        requests.post(FEISHU_WEBHOOK, json=card, timeout=10)
    except Exception:
        pass

# ====== App Bot??(????) ======
FEISHU_APP_ID = "cli_aaaccaa8ffb95cd9"
FEISHU_APP_SECRET = "YOUR_FEISHU_SECRET_HERE"
_app_token = None
_app_token_expiry = 0

def _get_app_token():
    global _app_token, _app_token_expiry
    if _app_token and time.time() < _app_token_expiry:
        return _app_token
    try:
        r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
        data = r.json()
        _app_token = data.get("tenant_access_token", "")
        _app_token_expiry = time.time() + data.get("expire", 7200) - 300
        return _app_token
    except Exception:
        return ""

def feishu_app_send(text, chat_id=None):
    """??App Bot????????"""
    try:
        if not chat_id:
            # ???????chat_id
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

content = content.replace(old_card_end, new_block)
with open("/home/ubuntu/scripts/agents/hermes_core.py", "w") as f:
    f.write(content)

import py_compile
py_compile.compile("/home/ubuntu/scripts/agents/hermes_core.py", doraise=True)
print("feishu_app_send added to hermes_core")
