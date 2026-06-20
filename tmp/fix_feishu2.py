with open("/home/ubuntu/scripts/agents/feishu_callback.py") as f:
    lines = f.readlines()

# Replace lines 368-389 (0-indexed: 367-388) with fixed analyze_one
new_func = [
    "        def analyze_one(sym):\n",
    "            try:\n",
    "                k1 = fetch_klines(sym, '1h', 100)\n",
    "                if len(k1) < 50: return None\n",
    "                c = [k['c'] for k in k1]\n",
    "                rs_arr = rsi(c)\n",
    "                rs = float(rs_arr[-1]) if isinstance(rs_arr, list) and len(rs_arr) > 0 else 50\n",
    "                cv = calc_cvd(k1, 6)\n",
    "                e20_arr = ema(c, 20); e50_arr = ema(c, 50)\n",
    "                e20 = float(e20_arr[-1]) if isinstance(e20_arr, list) and len(e20_arr) > 0 else c[-1]\n",
    "                e50 = float(e50_arr[-1]) if isinstance(e50_arr, list) and len(e50_arr) > 0 else c[-1]\n",
    "                price = c[-1]\n",
    "                trend = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')\n",
    "                score = 0; reasons = []\n",
    "                if cv > 20: score += 12; reasons.append('CVD??'+str(int(cv))+'%')\n",
    "                elif cv < -20: score -= 12; reasons.append('CVD??'+str(int(cv))+'%')\n",
    "                elif cv > 10: score += 6; reasons.append('CVD??'+str(int(cv))+'%')\n",
    "                elif cv < -10: score -= 6; reasons.append('CVD??'+str(int(cv))+'%')\n",
    "                if rs < 25: score += 12; reasons.append('RSI??'+str(int(rs)))\n",
    "                elif rs < 35: score += 6; reasons.append('RSI??'+str(int(rs)))\n",
    "                elif rs > 75: score -= 12; reasons.append('RSI??'+str(int(rs)))\n",
    "                elif rs > 65: score -= 6; reasons.append('RSI??'+str(int(rs)))\n",
    "                if trend == 'up': score += 8; reasons.append('????')\n",
    "                elif trend == 'down': score -= 8; reasons.append('????')\n",
    "                if abs(score) >= 12:\n",
    "                    return {'sym':sym,'signal':'long' if score>0 else 'short','score':score,\n",
    "                        'price':price,'reasons':reasons,'cvd':round(cv,1),'rsi':round(rs,0),'trend':trend}\n",
    "            except Exception as e:\n",
    "                pass\n",
    "            return None\n",
]

result = lines[:367] + new_func + lines[389:]

with open("/home/ubuntu/scripts/agents/feishu_callback.py", "w") as f:
    f.writelines(result)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/feishu_callback.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
