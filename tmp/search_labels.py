import json, os

data_dir = "/home/ubuntu/scripts/agents/mercu_data"
keywords = ["吸筹", "派发", "共振", "托底", "焦点", "陷阱", "背离", "洗盘", "多头", "空头"]

files = [f for f in os.listdir(data_dir) if f.endswith(".json") and not f.startswith("all_cookies") and not f.startswith("browser") and not f.startswith("latest") and not f.startswith("auth")]

for fname in sorted(files):
    fpath = os.path.join(data_dir, fname)
    try:
        with open(fpath) as f:
            text = f.read()
        found = [kw for kw in keywords if kw in text]
        if found:
            # Show context around first match
            first = text.find(found[0])
            ctx = text[max(0,first-80):first+120]
            print(f"{fname}: {found}")
            print(f"  context: ...{ctx}...")
            print()
        else:
            print(f"{fname}: none")
    except Exception as e:
        print(f"{fname}: ERROR {e}")
