"""Watchdog - monitors V2 daemon health and auto-restarts on failure."""
import sys, os, time, subprocess, json
from datetime import datetime

LOG_FILE = '/home/ubuntu/hermes-v2/logs/watchdog.log'


class Watchdog:
    def __init__(self, daemon_script=None):
        self.script = daemon_script or '/home/ubuntu/hermes-v2/daemon.py'
        self.max_restarts = 5   # max restarts per hour
        self.restart_window = 3600
        self.restart_history = []
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def log(self, msg):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{ts}] {msg}"
        print(line)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')

    def check_process(self):
        """Check if daemon process is running."""
        try:
            result = subprocess.run(['pgrep', '-f', self.script],
                                   capture_output=True, text=True, timeout=5)
            return bool(result.stdout.strip())
        except Exception:
            return False

    def can_restart(self):
        """Check if we haven't exceeded restart limit."""
        now = time.time()
        # Clean old entries
        self.restart_history = [t for t in self.restart_history if now - t < self.restart_window]
        return len(self.restart_history) < self.max_restarts

    def check_data_freshness(self, log_path, max_age=300):
        """Check if data log has been updated recently."""
        if not os.path.exists(log_path):
            return False
        mtime = os.path.getmtime(log_path)
        return (time.time() - mtime) < max_age

    def restart(self):
        """Restart the daemon."""
        if not self.can_restart():
            self.log(f"RESTART LIMIT REACHED ({len(self.restart_history)}/{self.max_restarts} per hour)")
            return False

        self.restart_history.append(time.time())
        self.log("RESTARTING daemon...")

        # Kill existing
        subprocess.run(['pkill', '-f', self.script], capture_output=True)
        time.sleep(2)

        # Start new
        subprocess.Popen(['python3', self.script],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.log(f"Daemon restarted (attempt {len(self.restart_history)}/{self.max_restarts})")
        return True

    def run_once(self):
        """Single watchdog check cycle."""
        running = self.check_process()
        if not running:
            self.log("Daemon NOT RUNNING!")
            self.restart()
            return

        # Check signal freshness
        signal_log = '/home/ubuntu/hermes-v2/logs/v2_signals.jsonl'
        fresh = self.check_data_freshness(signal_log, max_age=600)
        if not fresh:
            self.log(f"Signal log STALE (>10min)")
            self.restart()

    def run_loop(self, interval=120):
        """Run watchdog continuously."""
        self.log("Watchdog started")
        while True:
            try:
                self.run_once()
            except Exception as e:
                self.log(f"ERROR: {e}")
            time.sleep(interval)


if __name__ == '__main__':
    wd = Watchdog()
    wd.log("Watchdog starting...")
    wd.run_loop()
