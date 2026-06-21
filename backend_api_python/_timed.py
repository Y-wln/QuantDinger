import sys, os, time
sys.path.insert(0, '.')

t0 = time.time()
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType
print(f'event_bus import: {time.time()-t0:.2f}s')

t0 = time.time()
from app.services.hermes_strategies.signal_tracker import SignalTracker
print(f'signal_tracker import: {time.time()-t0:.2f}s')

bus = EventBus.get()
t0 = time.time()
tracker = SignalTracker()
print(f'SignalTracker init: {time.time()-t0:.2f}s')

# Test single emit
t0 = time.time()
bus.emit(Event(EventType.SIGNAL_GENERATED, {
    'symbol': 'TEST', 'direction': 'LONG', 'score': 30, 'price': 100.0,
    'reasons': ['test']
}, source='test'))
print(f'Single emit: {time.time()-t0:.2f}s')
print(f'Tracked: {len(tracker._signals)}')

# Test stats
t0 = time.time()
s = tracker.get_stats()
print(f'Stats: {time.time()-t0:.2f}s')

# Test save
t0 = time.time()
tracker.save()
print(f'Save: {time.time()-t0:.2f}s')

print('DONE - all fast')
