with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

changes = []

# 1. Lagging indicators: 1h CVD weight reduced
# OLD: cv > 20: score += 10; cv < -20: score -= 10
# NEW: reduced to 6
content = content.replace(
    "if cv > 20: score += 10; reasons.append('1hCVD??'+str(int(cv))+'%')",
    "if cv > 20: score += 6; reasons.append('1hCVD??'+str(int(cv))+'%')")
changes.append('1hCVD long: 10->6')

content = content.replace(
    "elif cv < -20: score -= 10; reasons.append('1hCVD??'+str(int(cv))+'%')",
    "elif cv < -20: score -= 6; reasons.append('1hCVD??'+str(int(cv))+'%')")
changes.append('1hCVD short: 10->6')

content = content.replace(
    "elif cv > 10: score += 5; reasons.append('1hCVD??'+str(int(cv))+'%')",
    "elif cv > 10: score += 3; reasons.append('1hCVD??'+str(int(cv))+'%')")
content = content.replace(
    "elif cv < -10: score -= 5; reasons.append('1hCVD??'+str(int(cv))+'%')",
    "elif cv < -10: score -= 3; reasons.append('1hCVD??'+str(int(cv))+'%')")
changes.append('1hCVD medium: 5->3')

# 2. CVD acceleration reduced
content = content.replace(
    "if cv > 10 and cv_accel == 'accelerating': score += 10; reasons.append('CVD????')",
    "if cv > 10 and cv_accel == 'accelerating': score += 6; reasons.append('CVD????')")
content = content.replace(
    "elif cv < -10 and cv_accel == 'accelerating': score -= 10; reasons.append('CVD????')",
    "elif cv < -10 and cv_accel == 'accelerating': score -= 6; reasons.append('CVD????')")
changes.append('CVD accel: 10->6')

# 3. Trend resonance reduced
content = content.replace(
    "if trend_1h == 'up' and trend_15m == 'up': score += 12; reasons.append('???????')",
    "if trend_1h == 'up' and trend_15m == 'up': score += 6; reasons.append('???????')")
content = content.replace(
    "elif trend_1h == 'down' and trend_15m == 'down': score -= 12; reasons.append('???????')",
    "elif trend_1h == 'down' and trend_15m == 'down': score -= 6; reasons.append('???????')")
changes.append('trend resonance: 12->6')

content = content.replace(
    "elif trend_1h == 'up': score += 6; reasons.append('1h????')",
    "elif trend_1h == 'up': score += 3; reasons.append('1h????')")
content = content.replace(
    "elif trend_1h == 'down': score -= 6; reasons.append('1h????')",
    "elif trend_1h == 'down': score -= 3; reasons.append('1h????')")
changes.append('1h trend solo: 6->3')

# 4. Leading indicators: OI boosted
content = content.replace(
    "score += 12; reasons.append('OI????(??OI?)')",
    "score += 18; reasons.append('OI????(??OI?)')")
content = content.replace(
    "score -= 12; reasons.append('OI????(??OI?)')",
    "score -= 18; reasons.append('OI????(??OI?)')")
changes.append('OI: 12->18')

content = content.replace(
    "if score > 0: score += 6; reasons.append('OI????')",
    "if score > 0: score += 10; reasons.append('OI????')")
content = content.replace(
    "if score < 0: score -= 6; reasons.append('OI????')",
    "if score < 0: score -= 10; reasons.append('OI????')")
changes.append('OI build: 6->10')

# 5. Orderbook boosted
content = content.replace(
    "if imb > 15: score += 8; reasons.append('?????')",
    "if imb > 15: score += 12; reasons.append('?????')")
content = content.replace(
    "elif imb < -15: score -= 8; reasons.append('?????')",
    "elif imb < -15: score -= 12; reasons.append('?????')")
changes.append('orderbook: 8->12')

# 6. 1m CVD boosted
content = content.replace(
    "if cvd1m > 15: score += 10; reasons.append('1m??')",
    "if cvd1m > 15: score += 15; reasons.append('1m??')")
content = content.replace(
    "else: score -= 10; reasons.append('1m??')",
    "else: score -= 15; reasons.append('1m??')")
changes.append('1mCVD: 10->15')

# 7. 5m volume boosted
content = content.replace(
    "if vr > 2.5: score += 10; reasons.append('5m??'+str(round(vr,1))+'x')",
    "if vr > 2.5: score += 15; reasons.append('5m??'+str(round(vr,1))+'x')")
content = content.replace(
    "elif vr > 1.8: score += 6; reasons.append('5m??'+str(round(vr,1))+'x')",
    "elif vr > 1.8: score += 10; reasons.append('5m??'+str(round(vr,1))+'x')")
content = content.replace(
    "elif vr > 1.3: score += 3; reasons.append('5m???'+str(round(vr,1))+'x')",
    "elif vr > 1.3: score += 5; reasons.append('5m???'+str(round(vr,1))+'x')")
changes.append('5m vol: 10/6/3 -> 15/10/5')

# 8. Taker boosted
content = content.replace(
    "if td == 'bullish': score += 8; reasons.append('??????')",
    "if td == 'bullish': score += 12; reasons.append('??????')")
content = content.replace(
    "elif td == 'bearish': score -= 8; reasons.append('??????')",
    "elif td == 'bearish': score -= 12; reasons.append('??????')")
changes.append('taker: 8->12')

# 9. Big order (tape) boosted
content = content.replace(
    "if lp > 0: score += 6; reasons.append('????')",
    "if lp > 0: score += 10; reasons.append('????')")
content = content.replace(
    "else: score -= 6; reasons.append('????')",
    "else: score -= 10; reasons.append('????')")
changes.append('big order: 6->10')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)

import py_compile, os
for d in ['/home/ubuntu/scripts/__pycache__', '/home/ubuntu/scripts/agents/__pycache__']:
    if os.path.exists(d):
        for f in os.listdir(d):
            if 'yaobi' in f:
                os.remove(os.path.join(d, f))
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('Reweight done:', changes)
