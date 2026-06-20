import os, subprocess
r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
for line in r.stdout.split("\n"):
    if "agent_orchestrator" in line and "grep" not in line:
        pid = line.split()[1]
        os.system(f"kill {pid} 2>/dev/null")
os.system("screen -ls | grep orch | cut -d. -f1 | xargs -r kill 2>/dev/null")
os.system("sleep 2")
os.system("screen -dmS orch bash -c 'cd ~/scripts/agents && python3 -B -u agent_orchestrator.py >> /tmp/orch.log 2>&1'")
print("clean restart done")
