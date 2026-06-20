import sys, time, traceback
sys.path.insert(0, '/home/ubuntu/hermes-v2')
print("Starting...")
try:
    from services.orchestrator import Orchestrator
    print("Import OK")
    orch = Orchestrator()
    print(f"Config loaded: {len(orch.cfg['scan_coins'])} coins, mode={orch.cfg['mode']}")
    print("Scanning...")
    signals = orch.scanner.scan_all()
    print(f"Got {len(signals)} signals")
    for sig in signals:
        print(f"  {sig['symbol']} score={sig['score']} dir={sig['direction']}")
except Exception as e:
    traceback.print_exc()
