#!/usr/bin/env python3
# Watchdog v2 - monitors ALL 8 services
import subprocess, time, os, json as j

SCREENS = {
    'orch': 'cd /home/ubuntu/scripts/agents && python3 -B -u agent_orchestrator.py',
    'fsc3': 'cd /home/ubuntu/scripts/agents && python3 -B -u feishu_callback.py',
    'yb7': 'python3 -B -u /home/ubuntu/scripts/yaobi_v8.py',
    'wsent': 'python3 -B -u /home/ubuntu/scripts/ws_sentinel.py',
    'sentinel': 'python3 -B -u /home/ubuntu/scripts/yaobi_sentinel.py',
    'liq': 'python3 -B -u /home/ubuntu/scripts/agents/liq_stream.py',
    'web': 'python3 -B /home/ubuntu/scripts/analyzer_web.py',
}

SCRIPTS = {k: v.split()[-1] for k, v in SCREENS.items()}
for k in ['orch','fsc3']:
    SCRIPTS[k] = '/home/ubuntu/scripts/agents/' + ('agent_orchestrator.py' if k == 'orch' else 'feishu_callback.py')
SCRIPTS['liq'] = '/home/ubuntu/scripts/agents/liq_stream.py'

FEISHU_WEBHOOK = 'https://open.feishu.cn/open-apis/bot/v2/hook/677e91cc-db83-4fc3-b953-b154aa4677fc'
_last_alert = {}

def alert(text):
    now = time.time()
    key = text[:20]
    if key in _last_alert and now - _last_alert[key] < 900:
        return
    _last_alert[key] = now
    try:
        import urllib.request
        data = j.dumps({'msg_type': 'text', 'content': {'text': '[Watchdog] ' + text}}).encode()
        urllib.request.urlopen(urllib.request.Request(FEISHU_WEBHOOK, data=data,
            headers={'Content-Type': 'application/json'}), timeout=10)
    except:
        pass

def check_syntax(filepath):
    try:
        r = subprocess.run(['python3', '-c', 'import py_compile; py_compile.compile("' + filepath + '", doraise=True)'],
            capture_output=True, text=True, timeout=15)
        return r.returncode == 0
    except:
        return False

while True:
    for name, cmd in SCREENS.items():
        r = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
        if '.' + name not in r.stdout:
            ts = time.strftime('%H:%M:%S')
            fpath = SCRIPTS.get(name, '')
            if fpath and os.path.exists(fpath) and not check_syntax(fpath):
                print('[' + ts + '] SKIP ' + name + ' - syntax error')
                alert('SKIP ' + name + ' - syntax error')
                continue
            print('[' + ts + '] Restarting ' + name)
            alert('Restarting ' + name)
            subprocess.Popen(['screen', '-dmS', name, 'bash', '-c', cmd + ' >> /tmp/' + name + '.log 2>&1'])
    time.sleep(60)
