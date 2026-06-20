import py_compile
with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    lines = f.readlines()
lines[199] = lines[199].replace('做多信号', '做空信号')
lines[208] = lines[208].replace('做多信号', '平仓记录')
with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.writelines(lines)
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('OK')
