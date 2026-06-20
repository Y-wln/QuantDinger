import os, py_compile

files = [
    '/home/ubuntu/scripts/agents/hermes_core.py',
    '/home/ubuntu/scripts/agents/entry_report.py',
    '/home/ubuntu/scripts/yaobi_paper.py',
]

for fp in files:
    with open(fp, 'rb') as f:
        data = f.read()
    data = data.replace(b'\xef\xbb\xbf', b'')
    with open(fp, 'wb') as f:
        f.write(data)
    print(fp, 'cleaned')

# Verify
for fp in files:
    try:
        py_compile.compile(fp, doraise=True)
        print(fp, 'compile OK')
    except Exception as e:
        print(fp, 'ERROR:', e)
