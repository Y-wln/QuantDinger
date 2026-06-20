p = '/home/ubuntu/scripts/yaobi_v8.py'
with open(p) as f:
    c = f.read()
c = c.replace('nm = parts[0]; sc = parts[1]; cv = parts[2]; rs = parts[3]; pr = parts[4]',
              'nm = parts[1]; sc = parts[2]; cv = parts[3]; rs = parts[4]; pr = parts[5]')
c = c.replace('reasons = parts[5] if len(parts) >= 7 else ""',
              'reasons = parts[6] if len(parts) >= 7 else ""')
with open(p, 'w') as f:
    f.write(c)
import py_compile
py_compile.compile(p, doraise=True)
print('fixed')
