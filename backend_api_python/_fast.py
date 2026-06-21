import sys, json, os, time
sys.path.insert(0, '.')

print('Loading data...', end=' ', flush=True)
data_dir = 'C:/Users/ZhuanZ/Documents/Codex/2026-06-06/hermes-agent-agent-agent/mercu_data'
with open(os.path.join(data_dir, 'anomaly-v4.json')) as f: raw = json.load(f)
with open(os.path.join(data_dir, 'momentum.json')) as f: momentum = json.load(f)
mercu = {'anomalies': raw.get('data', []), 'momentum': momentum}
print('OK')

from app.services.hermes_strategies import get_all_strategies, init_subscribers
from app.services.hermes_strategies.signal_tracker import SignalTracker
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType

init_subscribers()
bus = EventBus.get()
strategies = get_all_strategies()
tracker = SignalTracker()
print(f'Setup done, {bus.subscriber_count()} handlers, {len(strategies)} strategies')

print('Generating...', end=' ', flush=True)
for s in strategies:
    sigs = s.generate(mercu)
    for sig in sigs:
        bus.emit(Event(EventType.SIGNAL_GENERATED, sig.to_dict(), source=s.name))
    print(f'{s.name}={len(sigs)} ', end='', flush=True)
print()

print(f'Tracked: {len(tracker._signals)}')

for i, (sid, sig) in enumerate(tracker._signals.items()):
    entry = sig.entry_price if sig.entry_price > 0 else 1.0
    if sig.direction == 'LONG':
        tracker.close_signal(sid, entry * (1.03 if i % 2 == 0 else 0.98))
    else:
        tracker.close_signal(sid, entry * (0.97 if i % 2 == 0 else 1.02))

stats = tracker.get_stats()
print(f'WinRate: {stats["win_rate"]}% By source: {list(stats["by_source"].keys())} By indicator: {list(stats["by_indicator"].keys())[:5]}')
tracker.save()
print('ALL DONE')
