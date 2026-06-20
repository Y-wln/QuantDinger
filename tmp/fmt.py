import json, sys
d = json.load(sys.stdin)
for i, r in enumerate(d):
    desc = (r.get('description') or '')[:140]
    print(f'{i+1}. [{r["fullName"]}] *{r["stargazersCount"]}  {desc}')
