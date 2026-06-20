"""Scanner: scans coins and generates signals using indicators."""
import time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class Scanner:
    def __init__(self, config, kline_cache, scorer, alerts, decision_log):
        self.cfg = config
        self.kline = kline_cache
        self.scorer = scorer
        self.alerts = alerts
        self.dlog = decision_log
        self.coins = config.get('scan_coins', [])
        self._4h_klines = {}
        self._last_4h = 0

    def scan_one(self, symbol):
        """Scan a single coin, return signal or None."""
        try:
            # 4h cache refresh every hour
            now = time.time()
            if now - self._last_4h > 3600 or symbol not in self._4h_klines:
                k4 = self.kline.get(symbol, '4h', 300)
                if len(k4) >= 50:
                    self._4h_klines[symbol] = k4
            else:
                k4 = self._4h_klines.get(symbol, [])
            k1 = self.kline.get(symbol, '1h', 300)
            k5 = self.kline.get(symbol, '5m', 50)
            k15 = self.kline.get(symbol, '15m', 30)
            if len(k4) < 50 or len(k1) < 50:
                return None
            result = self.scorer.analyze(symbol, k4, k1, k5, k15)
            if result['signal'] != 'wait':
                self.dlog.signal_detected(symbol, result['score'],
                    result['direction'], result['price'], result['details'])
            return result
        except Exception as e:
            self.alerts.error(f'scan_one:{symbol}', str(e))
            return None

    def scan_all(self):
        """Scan all coins, return list of signals."""
        self._last_4h = time.time()
        signals = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(self.scan_one, sym): sym for sym in self.coins}
            for f in as_completed(futures):
                r = f.result()
                if r and r.get('signal') != 'wait':
                    signals.append(r)
        return sorted(signals, key=lambda x: abs(x['score']), reverse=True)
