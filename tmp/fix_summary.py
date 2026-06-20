with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    lines = f.readlines()

# Line 222 (1-indexed) = index 221 (0-indexed): pnl_emoji
lines[221] = '        pnl_emoji = "\U0001f4c8" if total_pnl >= 0 else "\U0001f4c9"\n'

# Line 223 = index 222: separator
lines[222] = '        report.append("  \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")\n'

# Line 224 = index 223: summary
lines[223] = '        report.append("  \u6301\u4ed3: {}/{} | {} \u76c8\u4e8f:{:+.1f}% | \u4ea4\u6613:{}\u7b14".format(len(positions), MAX_POS, pnl_emoji, total_pnl, state["trades"]))\n'

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.writelines(lines)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('OK')
