import sys, os
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add missing import
old_import = 'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,'
new_import = 'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,\n    DEFAULT_PARAMS, COIN_PARAMS,'
content = content.replace(old_import, new_import)
print('Import: fixed')

# 2. Reduce MAX_POS
content = content.replace('MAX_POS = 8       # ????', 'MAX_POS = 5       # ?????')

# 3. Update version to v12
content = content.replace('v11', 'v12')
content = content.replace('v10', 'v12')
content = content.replace('v8', 'v12')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 4. Clear pyc cache
import py_compile
cache_dir = '/home/ubuntu/scripts/__pycache__'
for f in os.listdir(cache_dir):
    if 'yaobi' in f:
        os.remove(os.path.join(cache_dir, f))
        print(f'Removed cache: {f}')

py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('yaobi_v8.py v12: compiled OK (fresh)')
