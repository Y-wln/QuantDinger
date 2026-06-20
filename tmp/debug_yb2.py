import sys

with open("/home/ubuntu/scripts/yaobi_v8.py", "r") as f:
    code = f.read()

old_debug = """    signals.sort(key=lambda x: abs(x['score']), reverse=True)
    # Debug: show top 8 scores
    if signals:
        top8 = [(s['sym'].replace('USDT',''), s['score'], ','.join(s.get('reasons',[])[:2])) for s in signals[:8]]
        print(f"  Top8: {' | '.join(f'{n}:{sc}({rs})' for n,sc,rs in top8)}")
    else:
        # Show any coin with non-zero score
        nonzero = [(s['sym'].replace('USDT',''), s['score'], ','.join(s.get('reasons',[])[:2])) for s in signals[:8]]
        print(f"  All scores below threshold, max was {signals[0]['sym'] if signals else 'none'} = {signals[0]['score'] if signals else 0}")
    new_signals = [s for s in signals if s['sym'] not in positions]"""

new_debug = """    signals.sort(key=lambda x: abs(x['score']), reverse=True)
    # Debug: show top scores
    if signals:
        top5 = [(s['sym'].replace('USDT',''), s['score']) for s in signals[:5]]
        print(f"  Top5: {' | '.join(f'{n}:{sc}' for n,sc in top5)}")
    else:
        print(f"  No signals above threshold (scanned {len(all_results)} coins)")
    new_signals = [s for s in signals if s['sym'] not in positions]"""

code = code.replace(old_debug, new_debug)

# Also need to capture all_results before filtering
old_all = "    for f in as_completed(futures, timeout=30):"
# Look for where results are collected
old_loop = """    for f in as_completed(futures):
            try:
                r = f.result()
                if r: signals.append(r)
            except: pass
    signals.sort(key=lambda x: abs(x['score']), reverse=True)"""

new_loop = """    all_results = []
    for f in as_completed(futures):
            try:
                r = f.result()
                if r: all_results.append(r)
            except: pass
    signals = [r for r in all_results if abs(r.get('score',0)) >= 15]
    signals.sort(key=lambda x: abs(x['score']), reverse=True)"""

if old_loop in code:
    code = code.replace(old_loop, new_loop)
    print("loop patched")
elif "all_results" in code:
    print("already has all_results")
else:
    print("WARNING: pattern not found")

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("yaobi debug patched OK")
