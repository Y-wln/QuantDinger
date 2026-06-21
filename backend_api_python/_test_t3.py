import sys, time
sys.path.insert(0, '.')
t0 = time.time()

from app.services.hermes_strategies.event_bus import EventBus, Event, EventType
from app.services.hermes_strategies.signal_tracker import SignalTracker

print(f'Import: {time.time()-t0:.2f}s')

bus = EventBus.get()
tracker = SignalTracker()
print(f'Init: {time.time()-t0:.2f}s')

# Inject signals
for i in range(20):
    sym = ['BTC','ETH','SOL','COAI','PLAY','MEGA'][i % 6]
    d = ['LONG','LONG','LONG','SHORT','SHORT','SHORT'][i % 6]
    sc = [35, 28, 22, -18, -15, -12][i % 6]
    bus.emit(Event(EventType.SIGNAL_GENERATED, {
        'symbol': sym, 'direction': d, 'score': sc,
        'price': 100.0 + i*1.5, 'reasons': ['OI吸筹','CVD强买']
    }, source='demon_v2'))

print(f'Emitted 20 signals: {time.time()-t0:.2f}s')
print(f'Tracked: {len(tracker._signals)}')

# Close some
for i, (sid, sig) in enumerate(tracker._signals.items()):
    if i < 12:
        mult = 1.05 if sig.direction == 'LONG' else 0.95
        tracker.close_signal(sid, sig.entry_price * mult)
    elif i < 16:
        mult = 0.97 if sig.direction == 'LONG' else 1.03
        tracker.close_signal(sid, sig.entry_price * mult)

s = tracker.get_stats()
print(f'Win rate: {s["win_rate"]}% ({s["wins"]}/{s["closed"]})')
print(f'By indicator: {list(s["by_indicator"].keys())}')
print(f'By coin: {list(s["by_coin"].keys())}')

tracker.save()
print(f'Total: {time.time()-t0:.2f}s')
print('ALL PASSED')
