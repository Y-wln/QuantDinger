import sys, json
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/agents/entry_report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Raise default threshold from 10 to 18
content = content.replace("DEFAULT_PARAMS = {'th': 10", "DEFAULT_PARAMS = {'th': 18")
print('DEFAULT_PARAMS th: 10->18')

# Fast coins from 8 to 12
for coin in ['INJUSDT','CHZUSDT','DASHUSDT','FETUSDT','ENAUSDT','PEPEUSDT','WIFUSDT','BONKUSDT']:
    old = "'" + coin + "':{'th':8,"
    new = "'" + coin + "':{'th':12,"
    if old in content:
        content = content.replace(old, new)
        print(f'{coin}: th 8->12')

# TAO from 10 to 14
content = content.replace("'TAOUSDT':{'th':10,", "'TAOUSDT':{'th':14,")
print('TAOUSDT: th 10->14')

with open('/home/ubuntu/scripts/agents/entry_report.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/entry_report.py', doraise=True)
print('entry_report.py: compiled OK')

# Reset yaobi state
with open('/home/ubuntu/scripts/yaobi_state.json', 'w') as f:
    json.dump({'positions':{}, 'pnl':0.0, 'trades':0}, f)
print('Yaobi state: RESET')
