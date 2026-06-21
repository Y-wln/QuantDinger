import subprocess, json

# Get token
result = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "cat", "/app/data/mercu_live_token.txt"], 
                       capture_output=True, text=True)
token = result.stdout.strip()
print(f"Token length: {len(token)}")

# Test API
import urllib.request
req = urllib.request.Request("https://cryptosniper-epic.zeabur.app/api/radar/anomaly-v4?limit=3")
req.add_header("Authorization", f"Bearer {token}")
try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    items = data if isinstance(data, list) else data.get("data", [])
    print(f"API OK: {resp.status} - {len(items)} anomalies")
    for item in items[:3]:
        print(f"  {item.get('sym','?')}: {item.get('score','?')}")
except Exception as e:
    print(f"API FAILED: {e}")
