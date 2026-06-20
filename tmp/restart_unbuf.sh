#!/bin/bash
screen -S v2 -X quit 2>/dev/null
sleep 2
screen -dmS v2 bash -c "cd /home/ubuntu/hermes-v2 && python3 -u daemon.py 2>&1 | tee /home/ubuntu/hermes-v2/logs/daemon_latest.log"
sleep 3
screen -ls | grep v2
ps aux | grep "daemon.py" | grep -v grep

