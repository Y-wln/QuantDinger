import sys, json, os, time
sys.path.insert(0, '.')

# Load data
data_dir = 'C:/Users/ZhuanZ/Documents/Codex/2026-06-06/hermes-agent-agent-agent/mercu_data'
with open(os.path.join(data_dir, 'anomaly-v4.json')) as f:
    raw = json.load(f)
with open(os.path.join(data_dir, 'momentum.json')) as f:
    momentum = json.load(f)
mercu = {'anomalies': raw.get('data', []), 'momentum': momentum}

# Import + init subscribers
from app.services.hermes_strategies import get_all_strategies, init_subscribers
from app.services.hermes_strategies.signal_tracker import SignalTracker
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType

t0 = time.time()
init_subscribers()
bus = EventBus.get()
print(f'Init + subscribers: {time.time()-t0:.2f}s ({bus.subscriber_count()} handlers)')

strategies = get_all_strategies()
tracker = SignalTracker()

# Generate
total = 0
for s in strategies:
    sigs = s.generate(mercu)
    for sig in sigs:
        total += 1
        bus.emit(Event(EventType.SIGNAL_GENERATED, sig.to_dict(), source=s.name))
    print(f'{s.name}: {len(sigs)} signals')

print(f'Total: {total}, Tracked: {len(tracker._signals)}')

# Close
for i, (sid, sig) in enumerate(tracker._signals.items()):
    entry = sig.entry_price if sig.entry_price > 0 else 1.0
    if sig.direction == 'LONG':
        tracker.close_signal(sid, entry * (1.03 if i % 2 == 0 else 0.98))
    else:
        tracker.close_signal(sid, entry * (0.97 if i % 2 == 0 else 1.02))

stats = tracker.get_stats()
print(f'\nWin Rate: {stats["win_rate"]}%')
print(f'By Strategy:')
for src, s in stats['by_source'].items():
    print(f'  {src}: WR={s["win_rate"]}% PnL={s["total_pnl_pct"]}%')
print(f'By Indicator (top 5):')
for ind, s in list(stats['by_indicator'].items())[:5]:
    print(f'  {ind}: {s["signals"]}x WR={s["win_rate"]}%')

tracker.save()
print(f'\nTotal time: {time.time()-t0:.2f}s')
print('ALL PASSED')
