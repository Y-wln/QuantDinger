import re
with open('/home/ubuntu/hermes-v2/services/mercu.py', 'r') as f:
    content = f.read()
content = content.replace(
    "data_dir or /home/ubuntu/scripts/agents/mercu_data",
    "data_dir or '/home/ubuntu/scripts/agents/mercu_data'"
)
with open('/home/ubuntu/hermes-v2/services/mercu.py', 'w') as f:
    f.write(content)
print("Fixed mercu.py path")
