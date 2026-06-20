import sys, os
sys.path.insert(0, "/home/ubuntu/hermes-v2")
os.chdir("/home/ubuntu/hermes-v2")
from indicators.rsi_v2 import score_rsi_divergence, rsi, detect_rsi_divergence
print("rsi_v2 OK")
print("RSI test:", rsi([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]))
print("Detect test:", detect_rsi_divergence.__doc__)
