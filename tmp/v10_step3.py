with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

old_long_sl = \"positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']*(1-SL_PCT),\n                'tp':s['price']*(1+TP_PCT),'time':now.isoformat(),'reasons':s['reasons']}\"
new_long_sl = \"atr_s = s.get('atr', 0.01); pat = s.get('params', DEFAULT_PARAMS); sl_p = pat['sl_atr']; tp_p = pat['tp_atr']\n            positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']-atr_s*sl_p,\n                'tp':s['price']+atr_s*tp_p,'time':now.isoformat(),'reasons':s['reasons']}\"
content = content.replace(old_long_sl, new_long_sl)

old_short_sl = \"positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']*(1+SL_PCT),\n                'tp':s['price']*(1-TP_PCT),'time':now.isoformat(),'reasons':s['reasons']}\"
new_short_sl = \"atr_s = s.get('atr', 0.01); pat = s.get('params', DEFAULT_PARAMS); sl_p = pat['sl_atr']; tp_p = pat['tp_atr']\n            positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']+atr_s*sl_p,\n                'tp':s['price']-atr_s*tp_p,'time':now.isoformat(),'reasons':s['reasons']}\"
content = content.replace(old_short_sl, new_short_sl)

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('Step 3: ATR SL/TP done')
