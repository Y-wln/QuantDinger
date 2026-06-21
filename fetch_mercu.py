import subprocess, json, os

# Get token from container
result = subprocess.run(['sudo', 'docker', 'exec', 'hermes-backend', 'cat', '/app/data/mercu_live_token.txt'], 
                       capture_output=True, text=True)
token = result.stdout.strip()

import urllib.request, ssl
ctx = ssl.create_default_context()
base = 'https://cryptosniper-epic.zeabur.app/api/radar'
dest = '/var/lib/docker/volumes/quantdinger_backend_data/_data'

for ep, fn in [('anomaly-v4?limit=100','mercu_anomalies.json'), ('momentum?window=15m','mercu_momentum.json'), ('surge?limit=20','mercu_surge.json')]:
    try:
        req = urllib.request.Request(f'{base}/{ep}', headers={'Authorization': f'Bearer {token}'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=25)
        data = resp.read()
        path = f'{dest}/{fn}'
        with open(path, 'wb') as f:
            f.write(data)
        print(f'{fn}: {len(data)}B')
    except Exception as e:
        print(f'{fn}: FAILED - {e}')

# Verify
os.system(f'ls -la {dest}/mercu_*.json')
