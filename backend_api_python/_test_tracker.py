import sys; sys.path.insert(0, '.')
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType

# Don't reset - we want subscribers active
EventBus.reset()
bus = EventBus.get()

# Import tracker (auto-subscribes to events)
from app.services.hermes_strategies.signal_tracker import SignalTracker, get_tracker

tracker = get_tracker()

# Simulate signals from strategy
print('=== Simulating 20 signals ===')
for i in range(20):
    symbols = ['BTC','ETH','SOL','COAI','PLAY','MEGA']
    directions = ['LONG','LONG','LONG','SHORT','SHORT','SHORT']
    scores = [35, 28, 22, -18, -15, -12]
    
    sym = symbols[i % 6]
    d = directions[i % 6]
    s = scores[i % 6]
    price = 100.0 + i * 1.5
    
    bus.emit(Event(EventType.SIGNAL_GENERATED, {
        'symbol': sym, 'direction': d, 'score': s,
        'price': price,
        'reasons': ['OI吸筹', 'CVD强买', 'MACD金叉', 'RSI bullish']
    }, source='demon_v2'))

print(f'Tracked: {len(tracker._signals)} signals')

# Simulate price updates and close some signals
for i, (sig_id, sig) in enumerate(tracker._signals.items()):
    if i < 12:  # Close first 12
        exit_price = sig.entry_price * (1.05 if sig.direction == 'LONG' else 0.95)
        tracker.close_signal(sig_id, exit_price)
    elif i < 16:  # Close 4 as losses
        exit_price = sig.entry_price * (0.97 if sig.direction == 'LONG' else 1.03)
        tracker.close_signal(sig_id, exit_price)

# Get stats
stats = tracker.get_stats()
print(f'\n=== Accuracy Report ===')
print(f'Total: {stats["total_signals"]} (open: {stats["open"]}, closed: {stats["closed"]})')
print(f'Win rate: {stats["win_rate"]}%')
print(f'Avg PnL: {stats["avg_pnl_pct"]}%')
print(f'Total PnL: {stats["total_pnl_pct"]}%')

print(f'\n=== By Strategy ===')
for src, s in stats['by_source'].items():
    print(f'  {src}: {s["win_rate"]}% WR ({s["wins"]}/{s["total"]}) PnL: {s["total_pnl_pct"]}%')

print(f'\n=== By Indicator ===')
for ind, s in list(stats['by_indicator'].items())[:8]:
    print(f'  {ind}: {s["signals"]} signals, {s["win_rate"]}% WR')

print(f'\n=== By Coin ===')
for coin, s in list(stats['by_coin'].items())[:6]:
    print(f'  {coin}: {s["total"]} trades, {s["win_rate"]}% WR')

# Test save/load
tracker.save()
loaded = tracker.load()
print(f'\nSave/Load: {loaded is not None}')
print(f'Loaded stats total: {loaded["stats"]["total_signals"]}')

# Test get_recent
recent = tracker.get_recent(5)
print(f'Recent signals: {len(recent)}')

print('\nALL SIGNAL TRACKER TESTS PASSED')
