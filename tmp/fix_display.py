# fix_yaobi_display.py - fix garbled display lines, use English+emoji
f = open('/home/ubuntu/scripts/agents/yaobi_pusher.py', 'rb')
data = f.read()
f.close()

# Convert to string, fix, write back
text = data.decode('utf-8-sig')
lines = text.split('\n')

# Find and replace display lines by pattern
for i, line in enumerate(lines):
    # Header line with V15
    if 'V15 | %s' in line and '--------' not in line:
        lines[i] = '            lines = ["----------------", "  \U0001f3af Yaobi Scan V15 | %s" % t, "----------------"]'
    # Long header
    if 'longs:' in line and i+3 < len(lines):
        if 'if longs' in lines[i+2] or 'lines.append' in lines[i+3]:
            # Find the append line
            for j in range(i, min(i+5, len(lines))):
                if 'lines.append' in lines[j] and ('long' in lines[j].lower() or 'M-iM' in lines[j]):
                    lines[j] = '                lines.append("  \U0001f7e2 === LONG ===")'
                    break
    if 'shorts:' in line and i+3 < len(lines):
        if 'if shorts' in lines[i+2] or 'lines.append' in lines[i+3]:
            for j in range(i, min(i+5, len(lines))):
                if 'lines.append' in lines[j] and ('short' in lines[j].lower() or 'M-iM' in lines[j]):
                    lines[j] = '                lines.append("  \U0001f534 === SHORT ===")'
                    break

result = '\n'.join(lines)
with open('/home/ubuntu/scripts/agents/yaobi_pusher.py', 'w', encoding='utf-8') as f:
    f.write(result)
print('Display lines fixed')
