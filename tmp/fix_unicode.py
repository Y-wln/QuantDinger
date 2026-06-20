# -*- coding: utf-8 -*-
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# Fix: correct unicode escapes in the alert message
old_bad = r"'  \\u2192 20s\u53d8\u52a8: ' + str(round(chg_pct, 1)) + '%' + (' \\U0001f4ca' if vol_surge else ''),"
# Actually the file might have single backslash. Let me check both
# If it was already patched, the line has \\u2192. If not, it has \u2192
# Let me just find the line and fix it

# Find the alert message line
lines = code.split('\n')
for i, line in enumerate(lines):
    if '20s变动' in line or '10s变动' in line:
        # Fix: use correct unicode
        lines[i] = "                '  \u2192 20s\u53d8\u52a8: ' + str(round(chg_pct, 1)) + '%' + (' \U0001f4ca' if vol_surge else ''),"
        break

code = '\n'.join(lines)

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('fixed unicode')
