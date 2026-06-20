import sys, json
sys.path.insert(0, '/home/ubuntu/hermes-v2')
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI

http = HTTPClient(retries=2, timeout=20)
ex = ExchangeAPI(http)

try:
    raw = ex.klines('BTCUSDT', '1h', 3)
    print(f'Type: {type(raw)}')
    print(f'Value: {json.dumps(raw, default=str)[:500]}')
except Exception as e:
    print(f'FAIL: {type(e).__name__}: {e}')
