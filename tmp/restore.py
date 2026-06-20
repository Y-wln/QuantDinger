import subprocess, os
os.chdir("/home/ubuntu/scripts")
subprocess.run(["git", "checkout", "--", "agents/agent_orchestrator.py"])
import py_compile
py_compile.compile("agents/agent_orchestrator.py", doraise=True)
print("restored OK")
