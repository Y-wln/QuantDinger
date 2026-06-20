import sys, time
sys.path.insert(0, '/home/ubuntu/hermes-v2')
from services.tracker import TrackerDaemon
t = TrackerDaemon()
print("V2 Tracker started")
while True:
    r = t.run_once()
    print(f"[{r['iso']}] {r['total_events']} events, {r['unique_coins']} coins")
    time.sleep(60)
