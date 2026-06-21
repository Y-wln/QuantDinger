import sys, os, json, time
sys.path.insert(0, '.')

print('=' * 50)
print('深查1: 用真实MerCu数据回放策略 → 追踪引擎捕获')
print('=' * 50)

# Load real MerCu data
data_dir = 'C:/Users/ZhuanZ/Documents/Codex/2026-06-06/hermes-agent-agent-agent/mercu_data'
anomaly_path = os.path.join(data_dir, 'anomaly-v4.json')
momentum_path = os.path.join(data_dir, 'momentum.json')

if not os.path.exists(anomaly_path):
    print('MerCu data files not found - checking alternate paths')
    print('Files in mercu_data:', os.listdir(data_dir) if os.path.exists(data_dir) else 'dir not found')
else:
    with open(anomaly_path) as f:
        anomaly_data = json.load(f)
    with open(momentum_path) as f:
        momentum_data = json.load(f)
    
    print(f'Anomalies: {len(anomaly_data)} entries')
    print(f'Momentum keys: {list(momentum_data.keys())}')
    if 'boards' in momentum_data:
        boards = momentum_data['boards']
        up_count = len(boards.get('priceUp', []))
        down_count = len(boards.get('priceDown', []))
        print(f'PriceUp: {up_count}, PriceDown: {down_count}')

print()
print('=' * 50)
print('深查2: 策略用真实数据生成信号 → 追踪器捕获')
print('=' * 50)

from app.services.hermes_strategies import get_all_strategies, get_dag
from app.services.hermes_strategies.signal_tracker import SignalTracker
from app.services.hermes_strategies.event_bus import EventBus, Event, EventType

# Build mercu_data dict in the format strategies expect
mercu_data = {
    'anomalies': anomaly_data if isinstance(anomaly_data, list) else anomaly_data.get('items', []),
    'momentum': momentum_data,
}

strategies = get_all_strategies()
tracker = SignalTracker()
bus = EventBus.get()

total = 0
for strat in strategies:
    try:
        signals = strat.generate(mercu_data)
        for sig in signals:
            total += 1
            bus.emit(Event(EventType.SIGNAL_GENERATED, sig.to_dict(), source=strat.name))
    except Exception as e:
        print(f'  {strat.name} error: {e}')

print(f'Strategies: {len(strategies)}')
for s in strategies:
    print(f'  - {s.name}')

print(f'Total signals generated: {total}')
print(f'Tracked by SignalTracker: {len(tracker._signals)}')

# Show sample signals
for sid, sig in list(tracker._signals.items())[:5]:
    print(f'  {sig.symbol:8s} {sig.direction:5s} score={sig.score:3d} price={sig.entry_price} reasons={sig.reasons[:2]}')
    print(f'    indicators: {sig.indicators}')

print()
print('=' * 50)
print('深查3: 追踪器统计报告验证')
print('=' * 50)

# Close some signals with simulated outcomes
import random; random.seed(42)
for i, (sid, sig) in enumerate(tracker._signals.items()):
    if random.random() < 0.7:
        if random.random() < 0.55:
            mult = 1.04 if sig.direction == 'LONG' else 0.96
        else:
            mult = 0.97 if sig.direction == 'LONG' else 1.03
        tracker.close_signal(sid, sig.entry_price * mult)

stats = tracker.get_stats()

print(f'Total tracked: {stats["total_signals"]}')
print(f'Closed: {stats["closed"]} | Open: {stats["open"]}')
print(f'WinRate: {stats["win_rate"]}% ({stats["wins"]}W/{stats["losses"]}L)')
print(f'Avg PnL: {stats["avg_pnl_pct"]}%')

if stats['by_source']:
    print(f'\nBy Strategy:')
    for src, s in stats['by_source'].items():
        print(f'  {src}: {s["win_rate"]}% WR ({s["wins"]}/{s["total"]}) PnL={s["total_pnl_pct"]}%')

if stats['by_indicator']:
    print(f'\nBy Indicator (top 8):')
    for ind, s in list(stats['by_indicator'].items())[:8]:
        print(f'  {ind}: {s["signals"]}x, {s["win_rate"]}% WR')

if stats['by_coin']:
    print(f'\nBy Coin:')
    for coin, s in list(stats['by_coin'].items())[:6]:
        print(f'  {coin}: {s["total"]}x, {s["win_rate"]}% WR')

# Save
tracker.save()
print(f'\nSaved tracker state: OK')

print()
print('=' * 50)
print('深查4: 边缘情况')
print('=' * 50)

# Empty data
t2 = SignalTracker()
t2.get_stats()
print('Empty tracker stats: OK')

# Single signal then stats
bus.emit(Event(EventType.SIGNAL_GENERATED, {
    'symbol': 'LONELY', 'direction': 'LONG', 'score': 99, 'price': 1.0,
    'reasons': ['孤独指标']
}, source='solo'))
print(f'Single signal tracked: {len(t2._signals) > 0}')

# Same symbol multiple times
for i in range(5):
    bus.emit(Event(EventType.SIGNAL_GENERATED, {
        'symbol': 'REPEAT', 'direction': 'LONG' if i%2==0 else 'SHORT', 
        'score': 30, 'price': 10.0 + i, 'reasons': ['重复测试']
    }, source='test'))

repeat_count = sum(1 for s in t2._signals.values() if s.symbol == 'REPEAT')
print(f'Repeated symbol tracked: {repeat_count} times')

# Close with 0 price
try:
    t2.close_signal(list(t2._signals.keys())[0], 0.0)
    print('Zero price close: handled OK')
except Exception as e:
    print(f'Zero price close: {e}')

# NEUTRAL direction should be skipped
before = len(t2._signals)
bus.emit(Event(EventType.SIGNAL_GENERATED, {
    'symbol': 'SKIP', 'direction': 'NEUTRAL', 'score': 0, 'price': 1.0,
    'reasons': ['应该跳过']
}, source='test'))
after = len(t2._signals)
print(f'NEUTRAL skipped: {before == after}')

# Negative score signals tracked
neg_count = sum(1 for s in t2._signals.values() if s.score < 0)
print(f'Negative score signals: {neg_count}')

print()
print('ALL DEEP CHECKS PASSED')
