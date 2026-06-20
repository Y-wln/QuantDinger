"""Backtest Sandbox - runs past data through V2 indicators without trading."""
import sys, os, time, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BacktestSandbox:
    """Replay historical klines through V2 scorer, track accuracy."""

    def __init__(self, exchange, scorer, start_date, end_date=None):
        self.ex = exchange
        self.scorer = scorer
        self.start = start_date
        self.end = end_date or datetime.now().strftime('%Y-%m-%d')
        self.results = []

    def run(self, symbol='BTCUSDT', interval='4h'):
        """Run backtest for a single symbol. Returns stats dict."""
        print(f"Backtesting {symbol} {interval} {self.start} -> {self.end}")

        # Fetch historical klines
        klines = self._fetch_historical(symbol, interval)
        if len(klines) < 100:
            print(f"  Insufficient data: {len(klines)} candles")
            return {'symbol': symbol, 'signals': 0, 'error': 'insufficient data'}

        signals = []
        correct = 0
        total = 0

        # Slide window: use last 100 candles as "history", score the next candle
        window = 100
        for i in range(window, len(klines) - 1):
            k4 = klines[i-window:i]  # historical context
            # Approximate smaller timeframes from 4h
            k1 = k4[-50:]  # last 50 candles as 1h proxy
            k5 = k4[-10:]  # last 10 as 5m proxy
            k15 = k4[-20:]  # last 20 as 15m proxy

            result = self.scorer.analyze(symbol, k4, k1, k5, k15)
            if result['signal'] == 'wait':
                continue

            # Forward check: what happened in the next candle?
            next_candle = klines[i + 1]
            entry = float(k4[-1]['c'])
            exit_price = float(next_candle['c'])
            direction = result['direction']
            pnl = (exit_price - entry) / entry * 100 if direction == 'long' else (entry - exit_price) / entry * 100

            total += 1
            if pnl > 0:
                correct += 1

            signals.append({
                'ts': next_candle.get('ts', i),
                'symbol': symbol,
                'direction': direction,
                'score': result['score'],
                'entry': entry,
                'exit': exit_price,
                'pnl_pct': round(pnl, 3),
                'win': pnl > 0,
                'leading': result.get('leading_signals', [])[:3]
            })

        win_rate = correct / total * 100 if total > 0 else 0
        avg_pnl = sum(s['pnl_pct'] for s in signals) / len(signals) if signals else 0

        stats = {
            'symbol': symbol,
            'interval': interval,
            'period': f'{self.start} -> {self.end}',
            'total_candles': len(klines),
            'signals': total,
            'wins': correct,
            'losses': total - correct,
            'win_rate': round(win_rate, 1),
            'avg_pnl_pct': round(avg_pnl, 3),
            'signals_detail': signals
        }

        print(f"  Signals: {total} | WinRate: {win_rate:.1f}% | AvgPnL: {avg_pnl:.3f}%")
        return stats

    def _fetch_historical(self, symbol, interval):
        """Fetch as many historical klines as possible."""
        all_klines = []
        # Binance max is 1500 per request, fetch in batches
        limit = 1000
        end_time = int(datetime.strptime(self.end, '%Y-%m-%d').timestamp() * 1000)
        start_time = int(datetime.strptime(self.start, '%Y-%m-%d').timestamp() * 1000)

        while end_time > start_time:
            try:
                raw = self.ex.klines(symbol, interval, min(limit, 1000))
                if not raw:
                    break
                all_klines = raw + all_klines
                # Update end_time to before the earliest fetched candle
                earliest_ts = raw[0]['ts'] if raw else end_time
                end_time = earliest_ts - 1
                if len(raw) < limit:
                    break
                time.sleep(0.5)  # rate limit
            except Exception as e:
                print(f"  Fetch error: {e}")
                break

        # Filter to date range
        filtered = [k for k in all_klines
                    if start_time <= k['ts'] <= int(datetime.strptime(self.end, '%Y-%m-%d').timestamp() * 1000)]
        return filtered

    def run_multi(self, symbols, interval='4h'):
        """Run backtest on multiple symbols."""
        for sym in symbols:
            stats = self.run(sym, interval)
            self.results.append(stats)
            time.sleep(1)  # rate limit
        return self.results

    def summary(self):
        """Print summary of all backtest results."""
        total_signals = sum(r.get('signals', 0) for r in self.results)
        total_wins = sum(r.get('wins', 0) for r in self.results)
        avg_wr = sum(r.get('win_rate', 0) for r in self.results if r.get('signals', 0) > 0)
        n = sum(1 for r in self.results if r.get('signals', 0) > 0)
        avg_wr = avg_wr / n if n > 0 else 0

        print(f"\n{'='*60}")
        print(f"BACKTEST SUMMARY | {len(self.results)} coins | {total_signals} signals")
        print(f"Total WinRate: {total_wins}/{total_signals} = {total_wins/total_signals*100:.1f}%" if total_signals > 0 else "No signals")
        print(f"Avg WinRate: {avg_wr:.1f}%")
        print(f"{'='*60}")
        for r in sorted(self.results, key=lambda x: x.get('win_rate', 0), reverse=True):
            s = r.get('signals', 0)
            if s > 0:
                print(f"  {r['symbol']:12s} WR:{r['win_rate']:5.1f}%  Signals:{s:4d}  AvgPnL:{r.get('avg_pnl_pct', 0):+.3f}%")
