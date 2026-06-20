"""Unified exchange API wrapper."""
import time, hmac, hashlib, os

class ExchangeAPI:
    def __init__(self, http, api_key=None, api_secret=None, testnet=False):
        self.http = http
        self.api_key = api_key or os.environ.get('BINANCE_API_KEY', '')
        self.api_secret = api_secret or os.environ.get('BINANCE_API_SECRET', '')
        base = 'https://testnet.binancefuture.com' if testnet else 'https://fapi.binance.com'
        self.base = base

    def _sign(self, params):
        qs = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(self.api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        return f"{qs}&signature={signature}"

    def _call(self, method, path, params=None, signed=False):
        url = f"{self.base}{path}"
        if signed:
            params = params or {}
            params['timestamp'] = int(time.time() * 1000)
            qs = self._sign(params)
            url = f"{url}?{qs}"
            headers = {'X-MBX-APIKEY': self.api_key}
        elif params:
            qs = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{qs}"
            headers = {}
        else:
            headers = {}
        if method in ('GET', 'DELETE'):
            return self.http.get(url, headers)
        elif method == 'POST':
            return self.http.post(url, {}, headers)

    def klines(self, symbol, interval, limit=100):
        """Fetch klines, return list of dicts {o,h,l,c,v,ts}."""
        raw = self._call('GET', '/fapi/v1/klines', {'symbol': symbol, 'interval': interval, 'limit': limit})
        return [{'o': float(k[1]), 'h': float(k[2]), 'l': float(k[3]),
                 'c': float(k[4]), 'v': float(k[5]), 'ts': k[0]} for k in raw]

    def price(self, symbol):
        return float(self._call('GET', '/fapi/v1/ticker/price', {'symbol': symbol})['price'])

    def open_interest(self, symbol):
        return float(self._call('GET', '/fapi/v1/openInterest', {'symbol': symbol})['openInterest'])

    def funding_rate(self, symbol):
        return float(self._call('GET', '/fapi/v1/fundingRate', {'symbol': symbol, 'limit': 1})[0]['fundingRate'])

    def account(self):
        return self._call('GET', '/fapi/v2/account', signed=True)

    def place_order(self, symbol, side, quantity, stop_loss=None, take_profit=None):
        params = {'symbol': symbol, 'side': side.upper(), 'type': 'MARKET', 'quantity': quantity}
        result = self._call('POST', '/fapi/v1/order', params, signed=True)
        if stop_loss:
            sl_side = 'SELL' if side.upper() == 'BUY' else 'BUY'
            self._call('POST', '/fapi/v1/order',
                       {'symbol': symbol, 'side': sl_side, 'type': 'STOP_MARKET',
                        'stopPrice': stop_loss, 'quantity': quantity, 'reduceOnly': 'true'}, signed=True)
        if take_profit:
            tp_side = 'SELL' if side.upper() == 'BUY' else 'BUY'
            self._call('POST', '/fapi/v1/order',
                       {'symbol': symbol, 'side': tp_side, 'type': 'TAKE_PROFIT_MARKET',
                        'stopPrice': take_profit, 'quantity': quantity, 'reduceOnly': 'true'}, signed=True)
        return result

    def positions(self):
        return self._call('GET', '/fapi/v2/positionRisk', signed=True)
