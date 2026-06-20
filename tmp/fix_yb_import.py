import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix import: DEFAULT_PARAMS and COIN_PARAMS are in entry_report, not hermes_core
old = "from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,\n    DEFAULT_PARAMS, COIN_PARAMS,"
new = "from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,\n    fetch_klines, fetch_oi, fetch_funding_rate, ema, rsi, calc_cvd, fetch_oi_history, fetch_taker_volume, fetch_long_short_ratio, fetch_fear_greed)\nfrom entry_report import DEFAULT_PARAMS, COIN_PARAMS"

content = content.replace(old, new)
print('Import: fixed correctly')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile, os
# Clear cache
for f in os.listdir('/home/ubuntu/scripts/__pycache__'):
    if 'yaobi' in f:
        os.remove(os.path.join('/home/ubuntu/scripts/__pycache__', f))
        print(f'Removed: {f}')

py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('yaobi_v8.py v12: compiled OK')
