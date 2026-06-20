with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

old_func = '''def get_candidates():
    \"\"\"从24hr ticker找高波动币\"\"\"
    try:
        data = proxy_mgr.fetch_json(BINANCE+'/api/v3/ticker/24hr', 15)
        if not data: return []
        candidates = []
        for t in data:
            sym = t.get('symbol','')
            if not sym.endswith('USDT'): continue
            name = sym.replace('USDT','')
            if name in SKIP: continue
            try:
                vol = float(t.get('quoteVolume',0))
                chg = float(t.get('priceChangePercent',0))
                if vol > 3e6 and abs(chg) > 3:
                    candidates.append((sym, vol, chg))
            except: pass
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:20]
    except:
        return []'''

new_func = '''def get_candidates():
    \"\"\"从24hr ticker找高波动币 - 涨幅榜+跌幅榜双路扫描\"\"\"
    try:
        data = proxy_mgr.fetch_json(BINANCE+'/api/v3/ticker/24hr', 15)
        if not data: return []
        gainers = []
        losers = []
        others = []
        for t in data:
            sym = t.get('symbol','')
            if not sym.endswith('USDT'): continue
            name = sym.replace('USDT','')
            if name in SKIP: continue
            try:
                vol = float(t.get('quoteVolume',0))
                chg = float(t.get('priceChangePercent',0))
                if vol > 1e6 and abs(chg) > 3:
                    item = (sym, vol, chg)
                    if chg > 8:
                        gainers.append(item)
                    elif chg < -8:
                        losers.append(item)
                    else:
                        others.append(item)
            except: pass
        gainers.sort(key=lambda x: x[2], reverse=True)
        losers.sort(key=lambda x: x[2])
        others.sort(key=lambda x: abs(x[2]), reverse=True)
        result = gainers[:8] + losers[:8] + others
        result = result[:25]
        return result
    except:
        return []'''

content = content.replace(old_func, new_func)
with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('OK: dynamic gainers+losers scan')
