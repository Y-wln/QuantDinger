"""PID lock to prevent double-start."""
import os, sys

def acquire_lock(pid_file=None):
    pid_file = pid_file or os.path.expanduser('~/hermes-v2/data/hermes.pid')
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            return False  # process still running
        except (OSError, ValueError, ProcessLookupError):
            pass
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    return True

def release_lock(pid_file=None):
    pid_file = pid_file or os.path.expanduser('~/hermes-v2/data/hermes.pid')
    try:
        os.remove(pid_file)
    except OSError:
        pass
