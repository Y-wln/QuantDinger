path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Adjust CVD to 1.5 (was 1.0, originally 2.0) - middle ground
old = "    if cv5 > 30: vl += 1.0; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -30: vs += 1.0; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))\n    elif cv5 > 15: vl += 0.5; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -15: vs += 0.5; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))"
new = "    if cv5 > 30: vl += 1.5; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -30: vs += 1.5; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))\n    elif cv5 > 15: vl += 0.8; rl.append(\"5mCVD_buy(%d%%)\" % int(cv5))\n    elif cv5 < -15: vs += 0.8; rs.append(\"5mCVD_sell(%d%%)\" % int(abs(cv5)))"
content = content.replace(old, new)

# Lower vote threshold from 2.5 to 2.0
content = content.replace("if vl >= 2.5: return \"long\"", "if vl >= 2.0: return \"long\"")
content = content.replace("if vs >= 2.5: return \"short\"", "if vs >= 2.0: return \"short\"")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("V18 tuned: CVD=1.5, threshold=2.0")
