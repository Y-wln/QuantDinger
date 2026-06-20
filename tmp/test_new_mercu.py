# Test MerCu bridge with actual data
import sys
sys.path.insert(0, "/home/ubuntu/hermes-v2")
from services.mercu import MerCuBridge

m = MerCuBridge()
print("Fresh:", m.is_fresh())
print()

# Anomalies
anomalies = m.get_anomalies(100)
print(f"Anomalies: {len(anomalies)}")
oi_count = sum(1 for a in anomalies if a.get("main_dim") == "oi")
vol_count = sum(1 for a in anomalies if a.get("main_dim") == "vol")
print(f"  OI events: {oi_count}, Vol events: {vol_count}")
for a in anomalies[:5]:
    print(f"  {a.get('sym','?'):8s} dim={a.get('main_dim','?'):5s} dir={a.get('main_direction',0):2d} grade={a.get('grade','?'):3s} {a.get('l1_sentence','')[:60]}")

# Signals
print()
signals = m.get_coin_signals()
print(f"Signals generated: {len(signals)}")
for s in signals[:10]:
    print(f"  {s['direction']:5s} {s['symbol']:12s} score={s['score']} {s['reasons']}")

# Surge
surge = m.get_surge(10)
print(f"\nSurge items: {len(surge)}")
for s in surge[:5]:
    print(f"  {s.get('sym','?'):8s} accel={s.get('accel',0):.1f} dir={s.get('dir','?')} rhythm={s.get('rhythm','?')}")
