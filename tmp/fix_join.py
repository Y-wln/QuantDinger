import sys
paths = sys.argv[1:] if len(sys.argv) > 1 else ['/home/ubuntu/scripts/yaobi_v8.py']
for path in paths:
    with open(path, 'r') as f:
        lines = f.readlines()
    new_lines = []
    skip = False
    for i, line in enumerate(lines):
        if skip:
            skip = False
            continue
        s = line.rstrip()
        if s.endswith("feishu_app_send('") and i+1 < len(lines) and "'.join(report))" in lines[i+1]:
            new_lines.append('        feishu_app_send(chr(10).join(report))\n')
            skip = True
        else:
            new_lines.append(line)
    with open(path, 'w') as f:
        f.writelines(new_lines)
    print('fixed:', path)
