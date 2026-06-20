lines = open('/home/ubuntu/scripts/agents/agent_orchestrator.py').readlines()
new_lines = []
skip = False
for line in lines:
    if '# Generate track_id for linking to outcome' in line:
        skip = True
        continue
    if skip:
        if 'ok, msg = self.position.open_position' in line:
            skip = False
            line = line.replace('track_id=tid', 'track_id=signal_id')
            new_lines.append(line)
        continue
    if 'track_id=tid' in line:
        line = line.replace('track_id=tid', 'track_id=signal_id')
    new_lines.append(line)
open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'w').writelines(new_lines)
print('fixed')
