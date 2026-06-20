import sys
sys.path.insert(0, "/home/ubuntu/hermes-v2")
from services.mercu import MerCuBridge

m = MerCuBridge()
print("Data dir:", m.data_dir)
print("Fresh:", m.is_fresh())

signals = m.get_coin_signals()
print("Signals:", len(signals))
for s in signals[:8]:
    print(f"  {s['direction']:5s} {s['symbol']:15s} score={s['score']} {s['reasons']}")
