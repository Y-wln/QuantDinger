import os, json, time, signal, sys, base64, requests

STATE_FILE = '/tmp/mercu_state/state.json'
API_URL = 'http://127.0.0.1:8888/api/hermes/mercu-token'
CLERK_REFRESH_URL = 'https://clerk.mercu.win/v1/client/sessions/{sid}/tokens?_clerk_js_version=6.18.1'
TOKEN_FILE = '/var/lib/docker/volumes/quantdinger_backend_data/_data/mercu_live_token.txt'
DATA_DIR = '/var/lib/docker/volumes/quantdinger_backend_data/_data'
INTERVAL = 30

running = True

def signal_handler(sig, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def load_state():
    with open(STATE_FILE) as f:
        state = json.load(f)
    client_cookie = None
    sid = None
    for c in state.get('cookies', []):
        if c['name'] == '__client' and '.clerk.mercu.win' in c.get('domain', ''):
            client_cookie = c['value']
        if c['name'] == '__session' and 'mercu.win' in c.get('domain', ''):
            try:
                parts = c['value'].split('.')
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
                sid = payload.get('sid', '')
            except:
                pass
    return client_cookie, sid

def refresh_jwt(client_cookie, sid):
    url = CLERK_REFRESH_URL.format(sid=sid)
    resp = requests.post(url, 
        headers={'Content-Type': 'application/json'},
        cookies={'__client': client_cookie},
        timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        return data.get('jwt', '')
    return ''

def write_token_to_volume(jwt):
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(jwt)
        os.chmod(TOKEN_FILE, 0o666)
        return True
    except PermissionError:
        try:
            import subprocess
            subprocess.run(['sudo', 'tee', TOKEN_FILE], input=jwt, capture_output=True, text=True)
            subprocess.run(['sudo', 'chmod', '666', TOKEN_FILE])
            return True
        except:
            return False
    except Exception as e:
        print(f'[daemon v5] Token file write failed: {e}')
        return False

def push_to_backend(jwt):
    try:
        resp = requests.post(API_URL, json={'token': jwt}, timeout=10)
        return resp.status_code == 200
    except:
        return False

def cache_mercu_data(jwt):
    headers = {'Authorization': f'Bearer {jwt}'}
    base = 'https://cryptosniper-epic.zeabur.app/api/radar'
    endpoints = [
        ('anomaly-v4?limit=100', 'mercu_anomalies.json'),
        ('momentum?window=15m', 'mercu_momentum.json'),
        ('surge?limit=20', 'mercu_surge.json'),
    ]
    import subprocess as _sp
    for ep, fn in endpoints:
        try:
            r = requests.get(f'{base}/{ep}', headers=headers, timeout=25)
            if r.status_code == 200:
                fpath = f'{DATA_DIR}/{fn}'
                try:
                    with open(fpath, 'w') as f:
                        f.write(r.text)
                except PermissionError:
                    _sp.run(['sudo', 'tee', fpath], input=r.text, capture_output=True, text=True)
                    _sp.run(['sudo', 'chmod', '666', fpath])
        except Exception:
            pass

def main():
    print('[daemon v5] Starting (Clerk API mode + direct volume write)...')
    if not os.path.exists(STATE_FILE):
        print(f'[daemon v5] FATAL: State file not found: {STATE_FILE}')
        sys.exit(1)
    client_cookie, sid = load_state()
    if not client_cookie or not sid:
        print('[daemon v5] FATAL: Missing client_cookie or sid')
        sys.exit(1)
    print(f'[daemon v5] sid={sid[:20]}... cookie={client_cookie[:30]}...')
    fail_count = 0
    while running:
        jwt = refresh_jwt(client_cookie, sid)
        if jwt:
            token_written = write_token_to_volume(jwt)
            api_ok = push_to_backend(jwt)
            if token_written:
                print(f'[daemon v5] Token refreshed + written to volume ({len(jwt)}B)')
                fail_count = 0
                cache_mercu_data(jwt)
            elif api_ok:
                print(f'[daemon v5] Token pushed via API ({len(jwt)}B)')
                fail_count = 0
            else:
                print('[daemon v5] Token write AND push both failed')
                fail_count += 1
        else:
            print(f'[daemon v5] Clerk refresh failed (fail {fail_count+1})')
            fail_count += 1
        if fail_count > 5:
            print('[daemon v5] Too many failures, exiting')
            sys.exit(1)
        time.sleep(INTERVAL)
    print('[daemon v5] Stopped')

if __name__ == '__main__':
    main()
