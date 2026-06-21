from app.data_providers.hermes_mercu import get_hermes_engine
e = get_hermes_engine()
a = e.get_anomalies(100)
s = e.get_surge(5)
p = e.get_plaza(10)
d = e.get_deep(5)
print(f"anom={len(a)} surge={len(s)} plaza={len(p)} deep={len(d)}")
sig = e.generate_signals()
print(f"signals={len(sig)}")
for x in a[:3]:
    sym = x.get("symbol", "?")
    sc = x.get("score", "?")
    print(f"  {sym}: {sc}")
