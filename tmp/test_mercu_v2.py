import sys
sys.path.insert(0, "/home/ubuntu/hermes-v2")
from services.mercu import MerCuBridge

m = MerCuBridge()
print("Data dir:", m.data_dir)
print("Fresh:", m.is_fresh())

# Test reading anomaly data
anomalies = m.get_anomalies(5)
print(f"Anomalies: {len(anomalies)}")
for a in anomalies[:3]:
    print(f"  {a}")

# Test OI flow for BTC
btc = m.get_oi_flow("BTCUSDT")
print(f"BTC OI flow: {btc}")

# Test OI flow for SOL
sol = m.get_oi_flow("SOLUSDT")
print(f"SOL OI flow: {sol}")

# Test momentum
mom = m.get_momentum()
if mom:
    print(f"Momentum keys: {list(mom.keys())[:5]}")
else:
    print("No momentum data")

# Test surge
surge = m.get_surge()
if surge:
    print(f"Surge keys: {list(surge.keys())[:5]}")
else:
    print("No surge data")
