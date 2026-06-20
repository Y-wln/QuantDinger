import sys
p = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/scripts/yaobi_v8.py'
with open(p, 'r') as f:
    code = f.read()
old = 'feishu_app_send(' + chr(10) + chr(39) + '.join(report))'
new = 'feishu_app_send(chr(10).join(report))'
count = code.count(old)
if count > 0:
    code = code.replace(old, new)
    with open(p, 'w') as f:
        f.write(code)
    print('fixed', count, 'occurrences')
else:
    print('no broken feishu_app_send found')
