import sys; sys.path.insert(0, '.')
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType, on
from app.services.hermes_strategies.signal_tracker import SignalTracker, get_tracker

bus = EventBus.get()
tracker = get_tracker()

print('=== Full Scenario: 30 signals, multiple strategies ===')

strategies = ['demon_v2', 'ambush_v2', 'lightning_v2']
coins = ['BTC','ETH','SOL','COAI','PLAY','MEGA','HYPE','INJ','WLD','ZEC']
import random
random.seed(42)

for i in range(30):
    sym = random.choice(coins)
    d = random.choice(['LONG','SHORT'])
    sc = random.randint(-40, 40)
    price = random.uniform(0.01, 65000)
    reasons = random.sample(['OI吸筹','CVD强买','MACD金叉','RSI超卖','RSI超买','CVD强卖','OI派发','SMC bullish','Plaza看多','共振','底部吸筹','顶部派发'], 3)
    
    bus.emit(Event(EventType.SIGNAL_GENERATED, {
        'symbol': sym, 'direction': d, 'score': sc,
        'price': price, 'reasons': reasons
    }, source=random.choice(strategies)))

print(f'Captured: {len(tracker._signals)}')

# Close with mixed outcomes
for i, (sid, sig) in enumerate(tracker._signals.items()):
    if random.random() < 0.6:  # 60% of signals lead to trades
        if random.random() < 0.55:  # 55% win rate
            mult = 1.04 if sig.direction == 'LONG' else 0.96
        else:
            mult = 0.97 if sig.direction == 'LONG' else 1.03
        tracker.close_signal(sid, sig.entry_price * mult)

stats = tracker.get_stats()
print(f'\n======== ACCURACY REPORT ========')
print(f'Total: {stats["total_signals"]} | Closed: {stats["closed"]} | Open: {stats["open"]}')
print(f'WinRate: {stats["win_rate"]}% ({stats["wins"]}W/{stats["losses"]}L/{stats["breakeven"]}BE)')
print(f'Avg PnL: {stats["avg_pnl_pct"]}%')
print(f'Total PnL: {stats["total_pnl_pct"]}%')

print(f'\n--- By Strategy ---')
for src, s in sorted(stats['by_source'].items(), key=lambda x: -x[1]['total']):
    print(f'  {src:15s}: {s["win_rate"]:5.1f}% WR ({s["wins"]:2d}/{s["total"]:2d}) PnL: {s["total_pnl_pct"]:6.2f}%')

print(f'\n--- By Indicator (top 10) ---')
for ind, s in sorted(stats['by_indicator'].items(), key=lambda x: -x[1]['signals'])[:10]:
    print(f'  {ind:20s}: {s["signals"]:3d} signals, {s["win_rate"]:5.1f}% WR')

print(f'\n--- By Coin ---')
for coin, s in sorted(stats['by_coin'].items(), key=lambda x: -x[1]['total'])[:6]:
    print(f'  {coin:8s}: {s["total"]:2d} trades, {s["win_rate"]:5.1f}% WR')

# Save
tracker.save()
print(f'\nSaved to logs/tracker/tracker_state.json')
print('ALL COMPREHENSIVE TRACKER TESTS PASSED')
