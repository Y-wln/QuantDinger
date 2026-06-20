# Order Book Imbalance
def fetch_orderbook_imbalance(symbol, depth=100):
    try:
        data = proxy_mgr.fetch_json(BINANCE + '/api/v3/depth?symbol=' + symbol + '&limit=' + str(depth), 8)
        if not data: return None
        bid_vol = sum(float(b[1]) for b in data.get('bids', []))
        ask_vol = sum(float(a[1]) for a in data.get('asks', []))
        if ask_vol <= 0: return None
        return {'ratio': round(bid_vol / ask_vol, 3), 'bid_vol': round(bid_vol, 0),
                'ask_vol': round(ask_vol, 0), 'imbalance': round((bid_vol - ask_vol) / (bid_vol + ask_vol) * 100, 1)}
    except: return None

# 1m CVD (ultra-fast)
def fetch_1m_cvd(symbol):
    try:
        k = fetch_klines(symbol, '1m', 30)
        if not k or len(k) < 10: return 0
        return calc_cvd(k, 6)
    except: return 0

# Tape Pressure from aggTrades
def fetch_tape_pressure(symbol):
    try:
        data = proxy_mgr.fetch_json(BINANCE + '/api/v3/aggTrades?symbol=' + symbol + '&limit=200', 8)
        if not data: return None
        buy_vol = 0; sell_vol = 0; large_trades = 0
        for t in data:
            qty = float(t.get('q', 0))
            price = float(t.get('p', 0))
            is_buyer = t.get('m', False)
            if is_buyer: buy_vol += qty * price
            else: sell_vol += qty * price
            if qty * price > 50000: large_trades += 1 if is_buyer else -1
        total = buy_vol + sell_vol
        if total <= 0: return None
        return {'buy_ratio': round(buy_vol / total, 3), 'total_vol': round(total, 0),
                'large_net': large_trades, 'pressure': 'bullish' if buy_vol/total > 0.55 else ('bearish' if buy_vol/total < 0.45 else 'neutral')}
    except: return None
