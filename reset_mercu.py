from app.data_providers.hermes_mercu import get_hermes_engine
e = get_hermes_engine()
e._circuit_breakers = {}
print("Circuit breakers reset")
e.refresh_all()
data = e.get_all_data()
for k, v in data.items():
    if isinstance(v, list):
        print(f"{k}: list len={len(v)}")
    elif isinstance(v, dict):
        print(f"{k}: dict keys={list(v.keys())[:5]}")
