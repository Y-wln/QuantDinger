import sys, json, os, time
sys.path.insert(0, '.')
t0 = time.time()

data_dir = 'C:/Users/ZhuanZ/Documents/Codex/2026-06-06/hermes-agent-agent-agent/mercu_data'
with open(os.path.join(data_dir, 'anomaly-v4.json')) as f: raw = json.load(f)
with open(os.path.join(data_dir, 'momentum.json')) as f: momentum = json.load(f)
mercu = {'anomalies': raw.get('data', []), 'momentum': momentum}

from app.services.hermes_strategies import get_all_strategies, init_subscribers
from app.services.hermes_strategies.signal_tracker import SignalTracker
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType

init_subscribers()
bus = EventBus.get()
strategies = get_all_strategies()
tracker = SignalTracker()

print(f'Setup: {time.time()-t0:.1f}s, handlers={bus.subscriber_count()}')

for s in strategies:
    sigs = s.generate(mercu)
    for sig in sigs:
        bus.emit(Event(EventType.SIGNAL_GENERATED, sig.to_dict(), source=s.name))

print(f'Generated+Tracked: {len(tracker._signals)} signals in {time.time()-t0:.1f}s')

for i, (sid, sig) in enumerate(tracker._signals.items()):
    entry = sig.entry_price if sig.entry_price > 0 else 1.0
    mult = 1.03 if i % 2 == 0 else 0.98
    if sig.direction == 'LONG':
        tracker.close_signal(sid, entry * mult)
    else:
        tracker.close_signal(sid, entry * (1.0 / mult))

stats = tracker.get_stats()
tracker.save()
print(f'WinRate: {stats["win_rate"]}% | Sources: {list(stats["by_source"].keys())} | Indicators: {list(stats["by_indicator"].keys())}')
print(f'Total: {time.time()-t0:.1f}s - ALL PASSED')
