import sys
sys.path.insert(0, '/home/ubuntu/hermes-v2')
errors = 0
modules = [
    'core.http_client','core.exchange','core.klines','core.config_loader',
    'core.alerts','core.state','core.pid_lock','core.decision_log',
    'indicators.bb','indicators.cvd','indicators.rsi','indicators.macd',
    'indicators.structure','indicators.volume','indicators.momentum',
    'indicators.candles','indicators.orderbook','indicators.smc',
    'indicators.hvn','indicators.oi_analysis','indicators.launch',
    'indicators.scorer',
    'services.scanner','services.filter','services.trader','services.monitor',
    'services.safety','services.orchestrator','services.dag','services.jin10',
    'services.yaobi','services.lightning','services.mercu','services.pusher',
    'services.tracker','services.ambush','services.demon','services.liquidation',
    'services.btc_vane','services.feishu_bridge','services.deepseek_bridge',
]
for m in modules:
    try:
        __import__(m)
        print(f'  OK {m}')
    except Exception as e:
        print(f'  FAIL {m}: {e}')
        errors += 1
print(f'\nTotal: {len(modules)} modules, {errors} errors')
