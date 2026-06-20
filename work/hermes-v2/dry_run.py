#!/usr/bin/env python3
"""V2 dry-run: scan + score, no trading, output signals."""
import sys, time, json
sys.path.insert(0, '/home/ubuntu/hermes-v2')

from services.orchestrator import Orchestrator

orch = Orchestrator()
orch.cfg['feishu_webhook'] = ''  # no feishu during test
orch.cfg['mode'] = 'dry-run'

print(f"V2 Dry-Run | {time.strftime('%Y-%m-%d %H:%M:%S')} | {len(orch.cfg['scan_coins'])} coins")
print("=" * 60)

for cycle in range(3):
    print(f"\n--- Cycle {cycle+1} ---")
    try:
        # Quick scan
        signals = orch.scanner.scan_all()
        for sig in signals:
            d = sig['direction']
            e = 'LONG' if d == 'long' else 'SHORT'
            print(f"  {e:6s} {sig['symbol']:12s} Score:{sig['score']:+4d}  ${sig['price']:.4f}")
            for k, v in list(sig['details'].items())[:4]:
                print(f"         {v}")
            # Check filter
            passed, reason = orch.filter.validate(sig)
            print(f"         Filter: {'PASS' if passed else 'BLOCK'} ({reason})")
    except Exception as e:
        print(f"  ERROR: {e}")
    if cycle < 2:
        time.sleep(30)

print(f"\n{'='*60}")
print("V2 Dry-Run Complete")
