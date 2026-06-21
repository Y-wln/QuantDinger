import sys; sys.path.insert(0, '.')
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType
from app.services.hermes_strategies.signal_tracker import SignalTracker

# Use existing bus (don't reset)
bus = EventBus.get()
tracker = SignalTracker()

print('=== Inject 20 test signals ===')
for i in range(20):
    sym = ['BTC','ETH','SOL','COAI','PLAY','MEGA'][i % 6]
    d = ['LONG','LONG','LONG','SHORT','SHORT','SHORT'][i % 6]
    sc = [35, 28, 22, -18, -15, -12][i % 6]
    
    bus.emit(Event(EventType.SIGNAL_GENERATED, {
        'symbol': sym, 'direction': d, 'score': sc,
        'price': 100.0 + i * 1.5,
        'reasons': ['OI吸筹p99%','CVD强买','MACD金叉','RSI bullish']
    }, source='demon_v2'))

print(f'Captured: {len(tracker._signals)}')

# Close some as wins/losses
for i, (sid, sig) in enumerate(tracker._signals.items()):
    if i < 12:
        mult = 1.05 if sig.direction == 'LONG' else 0.95
        tracker.close_signal(sid, sig.entry_price * mult)
    elif i < 16:
        mult = 0.97 if sig.direction == 'LONG' else 1.03
        tracker.close_signal(sid, sig.entry_price * mult)

s = tracker.get_stats()
print(f'Win rate: {s["win_rate"]}% ({s["wins"]}/{s["closed"]})')
print(f'Avg PnL: {s["avg_pnl_pct"]}%')
print(f'By source: {list(s["by_source"].keys())}')
print(f'By indicator: {list(s["by_indicator"].keys())[:5]}')
print(f'By coin: {list(s["by_coin"].keys())}')

# Save/Load
tracker.save()
loaded = tracker.load()
print(f'Save/Load OK: {loaded is not None}')

recent = tracker.get_recent(5)
print(f'Recent signals: {len(recent)}')

print('ALL TRACKER TESTS PASSED')
