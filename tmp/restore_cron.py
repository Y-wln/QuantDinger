import subprocess

cron = """0 3 * * * /home/ubuntu/.hermes/scripts/auto_backup.sh
0 9 * * * cd /home/ubuntu/.hermes/scripts && PYTHONPATH=/home/ubuntu/.hermes python3 ace_sync_lessons.py >> /tmp/ace_sync.log 2>&1
0 6 * * * cd /home/ubuntu/.hermes/scripts && python3 auto_backup.sh >> /tmp/backup.log 2>&1
0 4 * * * cd /home/ubuntu/.hermes/skills/hermes-dojo/scripts && python3 demo.py >> /tmp/dojo.log 2>&1
*/5 * * * * cd /home/ubuntu/hermes-v2 && python3 -c "from services.v2_tracker import check_results,summary; s,n=check_results(); print(f'Settled:{n}'); print(summary())" >> /tmp/v2_tracker.log 2>&1
*/10 * * * * cd /home/ubuntu/scripts/agents && python3 selfcheck_cron.py >> /tmp/selfcheck_cron.log 2>&1
0 3 * * * /home/ubuntu/.hermes/scripts/auto_backup.sh
* * * * * screen -S v2 -X select . 2>/dev/null || screen -dmS v2 bash -c "cd /home/ubuntu/hermes-v2 && python3 -u daemon.py 2>&1 | tee /home/ubuntu/hermes-v2/logs/daemon_latest.log"
* * * * * screen -S merculab -X select . 2>/dev/null || screen -dmS merculab python3 /home/ubuntu/mercu-lab/run.py --live
* * * * * screen -S fsc3 -X select . 2>/dev/null || screen -dmS fsc3 python3 -u /home/ubuntu/scripts/agents/feishu_callback.py
* * * * * screen -S liqws -X select . 2>/dev/null || screen -dmS liqws python3 -u /home/ubuntu/scripts/agents/liq_ws.py
*/2 * * * * cd /home/ubuntu/hermes-v2 && python3 -c "from services.pipeline_tracker import take_snapshots; take_snapshots()" >> /home/ubuntu/hermes-v2/logs/pipeline_cron.log 2>&1
"""

subprocess.run(['crontab', '-'], input=cron, text=True)
print('Crontab restored')
