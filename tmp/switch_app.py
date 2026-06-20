# 1. Patch feishu_callback to save chat_id
with open("/home/ubuntu/scripts/agents/feishu_callback.py") as f:
    content = f.read()

# Find route_command and add chat_id saving
old_route = "def route_command(text, chat_id):"
new_route = """def route_command(text, chat_id):
    try:
        with open("/tmp/feishu_chat_id", "w") as f:
            f.write(chat_id)
    except Exception:
        pass"""

content = content.replace(old_route, new_route)
with open("/home/ubuntu/scripts/agents/feishu_callback.py", "w") as f:
    f.write(content)
print("feishu_callback patched")

# 2. Switch yaobi to feishu_app_send
with open("/home/ubuntu/scripts/yaobi_v8.py") as f:
    yb = f.read()

yb = yb.replace(
    "from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send,",
    "from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send,"
)

yb = yb.replace("feishu_send(chr(10).join(report))", "feishu_app_send(chr(10).join(report))")
yb = yb.replace("feishu_send('??", "feishu_app_send('??")

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(yb)
print("yaobi switched to app bot")

import py_compile
py_compile.compile("/home/ubuntu/scripts/agents/hermes_core.py", doraise=True)
py_compile.compile("/home/ubuntu/scripts/agents/feishu_callback.py", doraise=True)
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("all compile OK")
