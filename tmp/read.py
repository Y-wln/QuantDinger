import json, sys
f = sys.argv[1]
d = json.load(open(f, encoding='utf-8-sig'))
for x in d:
    n = x['name']
    t = x['type']
    s = f" ({x['size']}B)" if t == 'file' else '/'
    print(f"  {n}{s}")
