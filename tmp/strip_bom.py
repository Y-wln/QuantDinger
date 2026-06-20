with open('/home/ubuntu/scripts/agents/hermes_core.py','rb') as f:
    data = f.read()
data = data.replace(b'\xef\xbb\xbf', b'')
with open('/home/ubuntu/scripts/agents/hermes_core.py','wb') as f:
    f.write(data)
print('BOM removed')
