import re
with open('/home/ubuntu/scripts/agents/feishu_callback.py', 'r') as f:
    content = f.read()
matches = [(m.start(), m.group()) for m in re.finditer(r'\?{3,}', content)]
print(f'Found {len(matches)} corrupted Chinese sequences')
for pos, txt in matches[:30]:
    line_num = content[:pos].count(chr(10)) + 1
    ctx = content[pos-15:pos+len(txt)+15].replace(chr(10), ' ')
    print(f'  L{line_num}: ...{ctx}...')
