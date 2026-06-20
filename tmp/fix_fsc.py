with open('/home/ubuntu/scripts/agents/feishu_callback.py', 'r') as f:
    content = f.read()

# Fix CVD labels (same pattern as yaobi)
content = content.replace(
    \"if cv > 20: score += 12; reasons.append('CVD??'+str(int(cv))+'%')\",
    \"if cv > 20: score += 12; reasons.append('CVD\u591a\u5934'+str(int(cv))+'%')\")
content = content.replace(
    \"elif cv < -20: score -= 12; reasons.append('CVD??'+str(int(cv))+'%')\",
    \"elif cv < -20: score -= 12; reasons.append('CVD\u7a7a\u5934'+str(int(cv))+'%')\")
content = content.replace(
    \"elif cv > 10: score += 6; reasons.append('CVD??'+str(int(cv))+'%')\",
    \"elif cv > 10: score += 6; reasons.append('CVD\u591a\u5934'+str(int(cv))+'%')\")
content = content.replace(
    \"elif cv < -10: score -= 6; reasons.append('CVD??'+str(int(cv))+'%')\",
    \"elif cv < -10: score -= 6; reasons.append('CVD\u7a7a\u5934'+str(int(cv))+'%')\")

# Fix RSI labels
content = content.replace(\"reasons.append('RSI??'+str(int(rs)))\", \"reasons.append('RSI\u8d85\u5356'+str(int(rs)))\")
# The above will fix all 4, but some should be 超卖 vs 超买
# Let me be more specific
content = content.replace(
    \"if rs < 25: score += 12; reasons.append('RSI\u8d85\u5356'+str(int(rs)))\",
    \"if rs < 25: score += 12; reasons.append('RSI\u8d85\u5356'+str(int(rs)))\")  # already replaced

# Actually the simpler approach won't work because all 4 RSI?? are same
# Let me do it line by line
lines = content.split('\n')
for i, line in enumerate(lines):
    if \"'RSI??'\" in line:
        if 'rs < 25' in line or 'rs < 35' in line:
            lines[i] = line.replace(\"'RSI??'\", \"'RSI\u8d85\u5356'\")
        elif 'rs > 75' in line or 'rs > 65' in line:
            lines[i] = line.replace(\"'RSI??'\", \"'RSI\u8d85\u4e70'\")
    if \"'????'\" in line:
        if \"trend == 'up'\" in line:
            lines[i] = line.replace(\"'????'\", \"'\u8d8b\u52bf\u5411\u4e0a'\")
        elif \"trend == 'down'\" in line:
            lines[i] = line.replace(\"'????'\", \"'\u8d8b\u52bf\u5411\u4e0b'\")
    # Also fix any CVD?? that might still remain
    if \"'CVD??'\" in line:
        if 'cv > 20' in line or 'cv > 10' in line:
            lines[i] = line.replace(\"'CVD??'\", \"'CVD\u591a\u5934'\")
        elif 'cv < -20' in line or 'cv < -10' in line:
            lines[i] = line.replace(\"'CVD??'\", \"'CVD\u7a7a\u5934'\")

content = '\n'.join(lines)
with open('/home/ubuntu/scripts/agents/feishu_callback.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/feishu_callback.py', doraise=True)
print('feishu_callback Chinese fixed')
