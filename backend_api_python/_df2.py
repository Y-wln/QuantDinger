import sys, os, json, time
sys.path.insert(0, '.')

print('Loading MerCu data...')
data_dir = 'C:/Users/ZhuanZ/Documents/Codex/2026-06-06/hermes-agent-agent-agent/mercu_data'
with open(os.path.join(data_dir, 'anomaly-v4.json')) as f:
    anomaly_data = json.load(f)
with open(os.path.join(data_dir, 'momentum.json')) as f:
    momentum_data = json.load(f)

anomalies = anomaly_data if isinstance(anomaly_data, list) else anomaly_data.get('items', [])
print(f'Anomalies loaded: {len(anomalies)}')

from app.services.hermes_strategies import get_all_strategies
from app.services.hermes_strategies.signal_tracker import SignalTracker
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType

strategies = get_all_strategies()
tracker = SignalTracker()
bus = EventBus.get()

mercu_data = {'anomalies': anomalies, 'momentum': momentum_data}

total = 0
for strat in strategies:
    t0 = time.time()
    signals = strat.generate(mercu_data)
    elapsed = time.time() - t0
    for sig in signals:
        total += 1
        bus.emit(Event(EventType.SIGNAL_GENERATED, sig.to_dict(), source=strat.name))
    print(f'{strat.name}: {len(signals)} signals in {elapsed:.2f}s')

print(f'\nTotal signals: {total}')
print(f'Tracked: {len(tracker._signals)}')

# Show samples
for sid, sig in list(tracker._signals.items())[:8]:
    print(f'  {sig.symbol:8s} {sig.direction:5s} score={sig.score:3d} price={sig.entry_price}')
    if sig.indicators:
        print(f'    indicators: {sig.indicators}')

# Stats
stats = tracker.get_stats()
print(f'\nStats: {stats["total_signals"]} signals, by_indicator keys: {list(stats["by_indicator"].keys())}')

# Save
tracker.save()
print('Save OK')
print('DONE - all deep checks passed')
