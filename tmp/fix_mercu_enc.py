import re

with open("/home/ubuntu/hermes-v2/services/mercu.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the garbled Chinese characters  
# The original Chinese: 吸筹, 建仓, 派发, 出货
# Fix None check for ai field
content = content.replace(
    'if "??" in ai or "??" in ai:',
    'if ai and ("吸筹" in ai or "建仓" in ai):'
)
content = content.replace(
    'elif "??" in ai or "??" in ai:',
    'elif ai and ("派发" in ai or "出货" in ai):'
)

# Also fix all garbled Chinese in context strings
replacements = {
    "OI??(??)": "OI暴涨(吸筹)",
    "OI??(????)": "OI暴涨(追高风险)",
    "OI??": "OI增加",
    "OI??(??)": "OI暴跌(出货)",
    "OI??(??)": "OI暴跌(洗盘)",
    "OI??": "OI减少",
    "Vol??(??)": "Vol爆发(点火)",
    "Vol??(??)": "Vol爆发(派发)",
    "Vol??": "Vol放大",
    "Surge????(??)": "Surge极速冒头(启动)",
    "Surge??": "Surge加速",
    "Plaza??(??)": "Plaza偏空(顶部)",
    "Plaza??(??)": "Plaza偏多(底部)",
    "AI:????": "AI:吸筹信号",
    "AI:????": "AI:派发信号",
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open("/home/ubuntu/hermes-v2/services/mercu.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed mercu.py encoding")
