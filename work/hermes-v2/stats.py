import os
sizes = []
base = '/home/ubuntu/hermes-v2'
for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if '__pycache__' not in d and 'logs' not in d and 'data' not in d]
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            path = os.path.join(root, f)
            with open(path) as fh:
                lines = len(fh.readlines())
            rel = os.path.relpath(path, base)
            sizes.append((rel, lines))
sizes.sort(key=lambda x: -x[1])
total = sum(s[1] for s in sizes)
for name, lines in sizes:
    if lines > 200: tag = 'RED'
    elif lines > 120: tag = 'YLW'
    else: tag = 'GRN'
    print(f'  [{tag}] {name:50s} {lines:4d}')
print(f'\n  Files: {len(sizes)}  Total: {total}  Avg: {total//len(sizes)}')
over200 = [s for s in sizes if s[1] > 200]
over150 = [s for s in sizes if s[1] > 150]
print(f'  >200行: {len(over200)}  >150行: {len(over150)}')
if over200:
    for n, l in over200:
        print(f'    {n}: {l}')
