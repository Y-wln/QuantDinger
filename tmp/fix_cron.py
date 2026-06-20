import subprocess
r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
cron = r.stdout
old = 'screen -dmS v2 python3 /home/ubuntu/hermes-v2/daemon.py'
new = 'screen -dmS v2 bash -c "cd /home/ubuntu/hermes-v2 && python3 -u daemon.py 2>&1 | tee /home/ubuntu/hermes-v2/logs/daemon_latest.log"'
cron = cron.replace(old, new)
subprocess.run(['crontab', '-'], input=cron, text=True)
print('OK')
for l in cron.split('\n'):
    if 'v2' in l:
        print(l)
