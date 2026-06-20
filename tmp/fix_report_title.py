with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    lines = f.readlines()

# Update startup message
for i, line in enumerate(lines):
    if '妖币扫描器v8 启动 | CVD+RSI趋势' in line:
        lines[i] = line.replace('CVD+RSI趋势 | 止损4% 止盈6%', '动态涨幅榜+跌幅榜 | CVD+RSI趋势')

# Update report title
for i, line in enumerate(lines):
    if 'report.append("  \u{1f3af} 妖币信号 | "' in line:
        lines[i] = line.replace('\u5996\u5e01\u4fe1\u53f7', '\u5996\u5e01\u626b\u63cf (\u6da8\u8dcc\u699c)')
        break

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.writelines(lines)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('OK')
