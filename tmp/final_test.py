import sys; sys.path.insert(0,'/home/ubuntu/scripts/agents')
from entry_report import entry_report
r = entry_report('BTCUSDT')
if r:
    print('OK score=' + str(r['score']) + ' sig=' + r['signal'])
    for k,v in sorted(r['dims'].items()):
        print('  ' + k + ': ' + v)
else:
    print('FAIL')
