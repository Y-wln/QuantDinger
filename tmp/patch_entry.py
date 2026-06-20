with open('/home/ubuntu/scripts/agents/entry_report.py', 'r') as f:
    content = f.read()

# Add imports
content = content.replace(
    "from hermes_core import (fetch_klines, fetch_oi_history, fetch_taker_volume, detect_launch,",
    "from hermes_core import (fetch_klines, fetch_oi_history, fetch_taker_volume, detect_launch, fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure,")

# Add leading signals section before signal determination
old = "    sig = 'long' if score>=th else ('short' if score<=-th else 'wait')"
new = """    # Order Book Imbalance (leading - shows intent before price moves)
    try:
        ob = fetch_orderbook_imbalance(sym, 100)
        if ob:
            imb = ob['imbalance']
            if imb > 20: score += 10; dims['订单簿'] = '+10 买方深度占优(' + str(imb) + '%)'
            elif imb < -20: score -= 10; dims['订单簿'] = '-10 卖方深度占优(' + str(imb) + '%)'
            elif imb > 10: score += 5; dims['订单簿'] = '+5 买方偏强(' + str(imb) + '%)'
            elif imb < -10: score -= 5; dims['订单簿'] = '-5 卖方偏强(' + str(imb) + '%)'
    except: pass

    # 1m CVD (fastest momentum)
    try:
        cv1 = fetch_1m_cvd(sym)
        if cv1 > 25: score += 12; dims['1mCVD'] = '+12 爆买' + str(int(cv1)) + '%'
        elif cv1 < -25: score -= 12; dims['1mCVD'] = '-12 爆卖' + str(int(cv1)) + '%'
        elif cv1 > 10: score += 6; dims['1mCVD'] = '+6 偏买' + str(int(cv1)) + '%'
        elif cv1 < -10: score -= 6; dims['1mCVD'] = '-6 偏卖' + str(int(cv1)) + '%'
    except: pass

    # Tape Pressure (actual market orders)
    try:
        tp = fetch_tape_pressure(sym)
        if tp:
            if tp['pressure'] == 'bullish': score += 8; dims['成交带'] = '+8 主动买盘'
            elif tp['pressure'] == 'bearish': score -= 8; dims['成交带'] = '-8 主动卖盘'
            if abs(tp.get('large_net', 0)) >= 3:
                if tp['large_net'] > 0: score += 6; dims['大单'] = '+6 大单净买' + str(tp['large_net'])
                else: score -= 6; dims['大单'] = '-6 大单净卖' + str(tp['large_net'])
    except: pass

    sig = 'long' if score>=th else ('short' if score<=-th else 'wait')"""

content = content.replace(old, new)
with open('/home/ubuntu/scripts/agents/entry_report.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/entry_report.py', doraise=True)
print('leading signals integrated')
