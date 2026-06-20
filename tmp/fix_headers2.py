with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    lines = f.readlines()
lines[199] = lines[199].replace('🟢 做空信号', '🔴 做空信号')
lines[208] = lines[208].replace('🟢 平仓记录', '📋 平仓记录')
with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.writelines(lines)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('OK')
