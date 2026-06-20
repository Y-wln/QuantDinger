"""K-line cache with auto-refresh."""
import time, threading

class KlineCache:
    def __init__(self, exchange):
        self.ex = exchange
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, symbol, interval, limit=100, max_age=60):
        key = f"{symbol}:{interval}"
        now = time.time()
        with self.lock:
            entry = self.cache.get(key)
            if entry and now - entry['ts'] < max_age and len(entry['data']) >= limit:
                return entry['data']
        try:
            data = self.ex.klines(symbol, interval, limit)
            with self.lock:
                self.cache[key] = {'data': data, 'ts': now}
            return data
        except Exception:
            with self.lock:
                entry = self.cache.get(key)
                if entry:
                    return entry['data']
            raise
