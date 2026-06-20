import base64
d = base64.b64decode(open("/tmp/run.b64").read())
open("/home/ubuntu/mercu-lab/run.py", "wb").write(d)
print("OK", len(d))
