import sys
sys.path.insert(0, '.')
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
http = HTTPClient(retries=2, timeout=15)
ex = ExchangeAPI(http)
try:
    k = ex.klines('BTCUSDT', '1h', 3)
    print(f'OK: {len(k)} klines, latest close={k[-1]["c"]}')
except Exception as e:
    print(f'FAIL: {e}')
