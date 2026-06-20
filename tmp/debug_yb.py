import sys

with open("/home/ubuntu/scripts/yaobi_v8.py", "r") as f:
    code = f.read()

# Find the signal processing section and add debug output
old_debug = """    signals.sort(key=lambda x: abs(x['score']), reverse=True)
    new_signals = [s for s in signals if s['sym'] not in positions]"""

new_debug = """    signals.sort(key=lambda x: abs(x['score']), reverse=True)
    # Debug: show top 8 scores
    if signals:
        top8 = [(s['sym'].replace('USDT',''), s['score'], ','.join(s.get('reasons',[])[:2])) for s in signals[:8]]
        print(f"  Top8: {' | '.join(f'{n}:{sc}({rs})' for n,sc,rs in top8)}")
    else:
        # Show any coin with non-zero score
        nonzero = [(s['sym'].replace('USDT',''), s['score'], ','.join(s.get('reasons',[])[:2])) for s in signals[:8]]
        print(f"  All scores below threshold, max was {signals[0]['sym'] if signals else 'none'} = {signals[0]['score'] if signals else 0}")
    new_signals = [s for s in signals if s['sym'] not in positions]"""

code = code.replace(old_debug, new_debug)

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("debug added OK")
