import os, re
base = '/home/ubuntu/hermes-v2'
std = {'sys','os','time','json','math','re','traceback','threading','signal',
       'datetime','hashlib','hmac','subprocess','urllib','yaml','concurrent',
       'glob','pathlib','argparse','random','ssl','typing','logging','io',
       'collections','functools','warnings','textwrap','http'}
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if '__pycache__' not in d and 'logs' not in d]
    for f in files:
        if not f.endswith('.py') or f == '__init__.py':
            continue
        path = os.path.join(root, f)
        rel = os.path.relpath(path, base)
        deps = set()
        with open(path) as fh:
            for line in fh:
                m = re.match(r'^\s*(?:from|import)\s+([\w.]+)', line)
                if m:
                    name = m.group(1).split('.')[0]
                    if name not in std:
                        deps.add(name)
        if deps:
            print(f'{rel:50s} -> {sorted(deps)}')
