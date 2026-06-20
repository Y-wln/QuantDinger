
import re

path = "/home/ubuntu/hermes-v2/daemon.py"
with open(path, encoding="utf-8-sig") as f:
    content = f.read()

# Add cooldown tracker before the MerCu section
insert_before = "        try:\n            mercu_signals = mercu.get_coin_signals()"

cooldown_code = """        # MerCu cooldown: skip push if top signals unchanged
        if "mercu_cooldown" not in dir():
            mercu_cooldown = {}
        mercu_now_ts = int(time.time() / 120) * 120  # 2min bucket
"""

content = content.replace(insert_before, cooldown_code + insert_before)

# Now add the cooldown check before the push
# Find "mercu_long = [s for s..." and add cooldown skip
old_long = "                mercu_long = [s for s in mercu_signals if s[\"direction\"] == \"long\"][:4]\n                mercu_short = [s for s in mercu_signals if s[\"direction\"] == \"short\"][:4]\n                msg_lines = [\"?? MerCu | \" + ts[-5:], \"©¥©¥©¥©¥©¥©¥©¥©¥©¥©¥©¥©¥\"]"

new_long = """                mercu_long = [s for s in mercu_signals if s["direction"] == "long"][:4]
                mercu_short = [s for s in mercu_signals if s["direction"] == "short"][:4]
                # Cooldown check: skip push if same top coins with same scores
                long_key = ",".join("{}={}".format(s["symbol"],s["score"]) for s in mercu_long)
                short_key = ",".join("{}={}".format(s["symbol"],s["score"]) for s in mercu_short)
                mercu_key = long_key + "|" + short_key
                mercu_prev = mercu_cooldown.get("key", "")
                mercu_last_push = mercu_cooldown.get("ts", 0)
                if mercu_key == mercu_prev and mercu_now_ts - mercu_last_push < 600:
                    mercu_signals = None  # skip push
                else:
                    mercu_cooldown["key"] = mercu_key
                    mercu_cooldown["ts"] = mercu_now_ts
                    msg_lines = ["?? MerCu | " + ts[-5:], "©¥©¥©¥©¥©¥©¥©¥©¥©¥©¥©¥©¥"]"""

content = content.replace(old_long, new_long)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Cooldown added")

