import sys
sys.path.insert(0, '/home/ubuntu/hermes-v2')
from services.yaobi import YaobiHunter, YAOBI_COINS
print(f"YAOBI_COINS: {len(YAOBI_COINS)} coins")
print("Import OK")
