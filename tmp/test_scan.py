import sys, traceback
sys.path.insert(0, "/home/ubuntu/scripts/agents")
exec(open("/home/ubuntu/scripts/yaobi_v8.py").read().split('if __name__')[0])

# Quick test of the scan function with traceback
try:
    scan()
except Exception as e:
    traceback.print_exc()
