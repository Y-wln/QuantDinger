import sys

with open("/home/ubuntu/scripts/yaobi_v8.py", "r") as f:
    code = f.read()

# Add debug before sorting - show what scores we got
old_line = "    # ?? + ??(??????)"
new_line = """    # Debug: show all scores found
    if signals:
        top_info = [(s['sym'].replace('USDT',''), s['score']) for s in sorted(signals, key=lambda x: abs(x['score']), reverse=True)[:8]]
        print(f"  Debug: {' | '.join(f'{n}={sc}' for n,sc in top_info)}")
    else:
        print(f"  Debug: 0 coins passed score threshold")
    # ?? + ??(??????)"""
code = code.replace(old_line, new_line)

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("debug added")
