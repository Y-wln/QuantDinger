#!/usr/bin/env python3
"""Hermes V2 - Trading System Entry Point.

Usage:
    python run.py                    # dry-run mode (default)
    python run.py --live             # live trading mode  
    python run.py --backtest DATE    # backtest from DATE (YYYY-MM-DD)
    python run.py --track            # tracker daemon only
    python run.py --test             # run indicator tests
"""
import sys, os, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_run(args):
    from services.orchestrator import Orchestrator
    orch = Orchestrator(args.config)
    if args.live:
        orch.cfg['mode'] = 'live'
    orch.run_loop()


def cmd_track(args):
    from services.tracker import TrackerDaemon
    import time
    t = TrackerDaemon()
    while True:
        result = t.run_once()
        total = result.get('total_events', 0)
        coins = result.get('unique_coins', 0)
        print(f"[{result['iso']}] Tracked {total} events across {coins} coins")
        time.sleep(60)


def cmd_test(args):
    """Run indicator tests."""
    import json
    from core.http_client import HTTPClient
    from core.exchange import ExchangeAPI
    from indicators.scorer import Scorer

    print("=== Hermes V2 Indicator Test ===\n")
    http = HTTPClient(retries=2, timeout=10)
    ex = ExchangeAPI(http)
    scorer = Scorer()

    test_coins = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT']
    for sym in test_coins:
        try:
            k4 = ex.klines(sym, '4h', 100)
            k1 = ex.klines(sym, '1h', 100)
            k5 = ex.klines(sym, '5m', 50)
            k15 = ex.klines(sym, '15m', 30)
            result = scorer.analyze(sym, k4, k1, k5, k15)
            direction = result['direction'].upper()
            emoji = '🟢' if direction == 'LONG' else ('🔴' if direction == 'SHORT' else '🟡')
            print(f"{emoji} {sym:10s} Score:{result['score']:+4d}  Signal:{result['signal']:6s}  ${result['price']:.4f}")
            for k, v in list(result['details'].items())[:5]:
                print(f"   {v}")
            if result['leading_signals']:
                print(f"   ⚡ Leading: {', '.join(result['leading_signals'][:3])}")
            print()
        except Exception as e:
            print(f"❌ {sym}: {e}\n")

    print("=== Test Complete ===")


def main():
    parser = argparse.ArgumentParser(description='Hermes V2 Trading System')
    parser.add_argument('--live', action='store_true', help='Live trading mode')
    parser.add_argument('--track', action='store_true', help='Tracker daemon only')
    parser.add_argument('--test', action='store_true', help='Run indicator tests')
    parser.add_argument('--config', type=str, default=None, help='Config file path')
    parser.add_argument('--backtest', type=str, nargs='?', const='2026-06-01',
                       help='Backtest from date')

    args = parser.parse_args()

    if args.test:
        cmd_test(args)
    elif args.track:
        cmd_track(args)
    else:
        cmd_run(args)


if __name__ == '__main__':
    main()
