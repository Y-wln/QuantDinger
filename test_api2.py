import subprocess, json

result = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "cat", "/app/data/mercu_live_token.txt"], capture_output=True, text=True)
token = result.stdout.strip()

import urllib.request
req = urllib.request.Request("https://cryptosniper-epic.zeabur.app/api/radar/anomaly-v4?limit=3")
req.add_header("Authorization", f"Bearer {token}")
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
print(json.dumps(data, indent=2)[:2000])
