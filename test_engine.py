from app.data_providers.hermes_mercu import get_hermes_engine
e = get_hermes_engine()
a = e.get_anomalies(100)
print(f"anomalies from engine: {len(a)}")
if a:
    print(f"  first: {a[0].get('sym','?')}")
else:
    print("  EMPTY!")
    # Debug: check client
    print(f"  client token len: {len(e.client.token)}")
    print(f"  circuit breaker open: {e.client.circuit.is_open}")
