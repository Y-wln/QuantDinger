from app.data_providers.hermes_mercu import HermesSignalEngine
e = HermesSignalEngine()
d = e.get_all_data()
for k, v in d.items():
    if isinstance(v, list):
        print(f"{k}: list len={len(v)}")
    elif isinstance(v, dict):
        keys = list(v.keys())[:5]
        print(f"{k}: dict keys={keys}")
    else:
        print(f"{k}: {type(v).__name__}")
