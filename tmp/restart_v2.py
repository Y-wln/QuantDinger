
import subprocess, time
subprocess.run(['screen', '-S', 'v2', '-X', 'quit'])
time.sleep(2)
subprocess.run(['screen', '-dmS', 'v2', 'bash', '-c', 'cd /home/ubuntu/hermes-v2 && python3 daemon.py 2>&1 | tee /home/ubuntu/hermes-v2/logs/daemon_latest.log'])
time.sleep(4)
result = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
print(result.stdout)
result2 = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
for line in result2.stdout.split('\n'):
    if 'daemon.py' in line and 'grep' not in line:
        print(line)

