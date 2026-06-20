with open("/home/ubuntu/scripts/agents/agent_orchestrator.py") as f:
    lines = f.readlines()

# Find key line numbers
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith("def monitor_positions"):
        print(f"L{i+1}: monitor_positions")
    if s.startswith("def process_signals"):
        print(f"L{i+1}: process_signals")
    if s.startswith("def run("):
        print(f"L{i+1}: run")
    if "price<=p['sl']" in s and "direction==" in s:
        print(f"L{i+1}: SL check [{s[:60]}]")
    if "Live PnL update" in s:
        print(f"L{i+1}: Live PnL")
    if "save_state" in s and "position" in s:
        print(f"L{i+1}: save_state [{s[:60]}]")
