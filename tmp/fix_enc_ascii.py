# ASCII-only fix script for yaobi_pusher.py encoding
import re

path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8-sig") as f:
    lines = f.readlines()

# Line patterns to fix (find by unique markers)
new_lines = []
for line in lines:
    # Fix header: "  [garbled] V15 | %s"
    if 'V15 | %s' in line and '--------' not in line:
        # Replace with correct Unicode
        before_v15 = line.split('V15 | %s')[0]
        after_v15 = line.split('V15 | %s')[1] if 'V15 | %s' in line else ''
        line = '\u0020\u0020\U0001f3af\u0020\u5996\u5e01\u626b\u63cf V15 | %s' + after_v15
    
    # Fix long section header
    if '\u505a\u591a\u4fe1\u53f7' in line or 'long_signal' in line.lower():
        pass  # we will fix by looking for specific garbled patterns
    
    new_lines.append(line)

# Actually, let me just fix the 3 most visible garbled patterns
content = "".join(new_lines)

# Pattern 1: The main header with target emoji
# Find line containing "V15 | %s" and not "--------"
content = content.replace(
    '  \u9983\u5e46 \u6f61\u6a7c\u7a67\u998e\u5dee\u82a3\u5bbf V15',
    '  \U0001f3af \u5996\u5e01\u626b\u63cf V15'
)

print("Fixed header line")
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
