import json, sys, re

fname = sys.argv[1]
with open(fname, encoding="utf-8-sig") as f:
    d = json.load(f)
for i, r in enumerate(d):
    desc = (r.get("description") or "")[:140]
    desc = re.sub(r'[^\x00-\x7F\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', '', desc)
    stars = r.get("stargazersCount", 0)
    print("{}. [{}] *{}  {}".format(i+1, r['fullName'], stars, desc))