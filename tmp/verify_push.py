import py_compile, os
os.system('rm -f /home/ubuntu/scripts/agents/__pycache__/signal_pusher*')
py_compile.compile('/home/ubuntu/scripts/agents/signal_pusher.py', doraise=True)
print('signal_pusher.py: OK')
