import sys, time, traceback, signal
sys.path.insert(0, '/home/ubuntu/hermes-v2')

# Timeout wrapper
def timeout_handler(signum, frame):
    raise TimeoutError("Scan timed out")

signal.signal(signal.SIGALRM, timeout_handler)

from services.orchestrator import Orchestrator

orch = Orchestrator()
orch.cfg['feishu_webhook'] = ''
orch.cfg['mode'] = 'dry-run'

print(f"V2 Dry-Run | {time.strftime('%H:%M:%S')} | {len(orch.cfg['scan_coins'])} coins")
print("=" * 50)

for cycle in range(2):
    print(f"\n--- Cycle {cycle+1} ---")
    try:
        signal.alarm(45)
        signals = orch.scanner.scan_all()
        signal.alarm(0)
        print(f"  Signals: {len(signals)}")
        for sig in signals:
            d = sig['direction']
            e = 'LONG' if d == 'long' else 'SHORT'
            print(f"  {e:6s} {sig['symbol']:12s} Score:{sig['score']:+4d}  ${sig['price']:.4f}")
            for k, v in list(sig['details'].items())[:4]:
                print(f"         {v}")
            passed, reason = orch.filter.validate(sig)
            print(f"         Filter: {'PASS' if passed else 'BLOCK'} ({reason})")
    except TimeoutError:
        signal.alarm(0)
        print("  TIMEOUT")
    except Exception as e:
        signal.alarm(0)
        print(f"  ERROR: {e}")
    if cycle < 1:
        time.sleep(10)

print(f"\nDone at {time.strftime('%H:%M:%S')}")
