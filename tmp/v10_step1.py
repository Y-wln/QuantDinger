import sys
with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

# 1. Add atr to imports
content = content.replace(
    'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands,',
    'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,')

# 2. Add per-coin config
old_cfg = 'MAX_POS = 8       # 最高持仓\nSL_PCT = 0.04     # 止损4%\nTP_PCT = 0.06     # 止盈6%'
new_cfg = '''MAX_POS = 8       # 最高持仓
SL_PCT = 0.04     # 止损4% (fallback)
TP_PCT = 0.06     # 止盈6% (fallback)

# v10: 逐币参数 threshold / ATR止损倍数 / ATR止盈倍数 / fast=15m先行
COIN_PARAMS = {
    'INJUSDT':  {'th': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'CHZUSDT':  {'th': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'DASHUSDT': {'th': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'TAOUSDT':  {'th': 10, 'sl_atr': 2.5, 'tp_atr': 4.0, 'fast': True},
    'FETUSDT':  {'th': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'ENAUSDT':  {'th': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'ONDOUSDT': {'th': 10, 'sl_atr': 2.5, 'tp_atr': 4.0, 'fast': False},
    'TONUSDT':  {'th': 12, 'sl_atr': 2.0, 'tp_atr': 3.5, 'fast': False},
    'PEPEUSDT': {'th': 8,  'sl_atr': 3.5, 'tp_atr': 6.0, 'fast': True},
    'WIFUSDT':  {'th': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'BONKUSDT': {'th': 8,  'sl_atr': 3.5, 'tp_atr': 6.0, 'fast': True},
}
DEFAULT_PARAMS = {'th': 10, 'sl_atr': 2.0, 'tp_atr': 3.5, 'fast': False}'''
content = content.replace(old_cfg, new_cfg)

print('Step 1-2 done')
with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)
print('Saved')
