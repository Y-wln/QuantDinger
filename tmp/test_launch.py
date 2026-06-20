import sys; sys.path.insert(0,'/home/ubuntu/scripts/agents')
from entry_report import entry_report
for sym in ['BTCUSDT','ETHUSDT','SOLUSDT','DASHUSDT','INJUSDT','CHZUSDT']:
    r = entry_report(sym)
    if r:
        launch = r['dims'].get('LAUNCH', '')
        print(r['sym'], 'sig='+r['signal'], 'score='+str(r['score']), 'entry_ok='+str(r['entry_ok']), 'launch='+launch)
    else:
        print(sym, 'FAIL')
