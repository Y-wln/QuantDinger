with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

old = 'bb = bollinger_bands(c, 20, 2); bb_bw = bb[\" bandwidth] if bb else 50; bb_squeeze = bb.get(squeeze, False) if bb else False\n        bb_squeeze = bb_bw < 8'
new = 'bb = bollinger_bands(c, 20, 2)\n        bb_bw = bb[\"bandwidth\"] if bb else 50\n        bb_squeeze = bb.get(\"squeeze\", False) if bb else False'
content = content.replace(old, new)

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('OK')
