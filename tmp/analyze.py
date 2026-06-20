import json, os, time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# === Pipeline Tracker ===
ppath = "/home/ubuntu/hermes-v2/logs/pipeline_tracker.json"
d = json.load(open(ppath))
pipes = d["pipelines"]
active = [p for p in pipes if p["status"] == "active"]
early = [p for p in pipes if p["status"] == "early"]
settled = [p for p in pipes if p.get("settled")]

print("=" * 60)
print("PIPELINE TRACKER ANALYSIS")
print("=" * 60)
print("Total: {} | Active: {} | Early: {} | Settled: {}".format(
    len(pipes), len(active), len(early), len(settled)))

wins = [p for p in settled if p.get("resolution") == "win"]
losses = [p for p in settled if p.get("resolution") == "loss"]
if settled:
    print("Wins: {} | Losses: {} | WR: {:.1f}%".format(
        len(wins), len(losses), len(wins)/len(settled)*100))
    if wins:
        avg_win = sum(p.get("final_pnl_pct", 0) for p in wins) / len(wins)
        avg_mfe = sum(p.get("mfe_pct", 0) for p in wins) / len(wins)
        print("Avg Win: +{:.2f}% | Avg MFE: +{:.2f}%".format(avg_win, avg_mfe))
    if losses:
        avg_loss = sum(p.get("final_pnl_pct", 0) for p in losses) / len(losses)
        print("Avg Loss: {:.2f}%".format(avg_loss))

# By source
print("\n--- By Source ---")
srcs = Counter(p.get("signal_source", "?") for p in pipes)
for k, v in srcs.most_common():
    src_pipes = [p for p in pipes if p.get("signal_source") == k]
    src_settled = [p for p in src_pipes if p.get("settled")]
    src_wins = [p for p in src_settled if p.get("resolution") == "win"]
    wr = len(src_wins)/len(src_settled)*100 if src_settled else 0
    print("  {}: {} total, {} settled, WR {:.0f}%".format(k, v, len(src_settled), wr))

# By direction
print("\n--- By Direction ---")
for dname in ["long", "short"]:
    dpipes = [p for p in pipes if p.get("direction") == dname]
    dsettled = [p for p in dpipes if p.get("settled")]
    dwins = [p for p in dsettled if p.get("resolution") == "win"]
    print("  {}: {} total, {} settled, WR {:.0f}%".format(dname, len(dpipes), len(dsettled),
        len(dwins)/len(dsettled)*100 if dsettled else 0))

# Early-to-signal conversion
with_early = [p for p in pipes if p.get("early_time")]
early_confirmed = [p for p in with_early if p.get("signal_time")]
print("\n--- Early Detection ---")
print("  Total early: {} | Confirmed: {} | Rate: {:.0f}%".format(
    len(with_early), len(early_confirmed),
    len(early_confirmed)/len(with_early)*100 if with_early else 0))

# Top performing symbols
print("\n--- Top/Bottom Symbols (settled only) ---")
sym_stats = defaultdict(list)
for p in settled:
    sym_stats[p.get("symbol","?")].append(p.get("final_pnl_pct", 0))
sym_avg = {k: sum(v)/len(v) for k, v in sym_stats.items() if len(v) >= 2}
for sym, avg in sorted(sym_avg.items(), key=lambda x: -x[1])[:5]:
    print("  {}: avg +{:.2f}% ({} trades)".format(sym, avg, len(sym_stats[sym])))
print("  ...")
for sym, avg in sorted(sym_avg.items(), key=lambda x: x[1])[:5]:
    print("  {}: avg {:.2f}% ({} trades)".format(sym, avg, len(sym_stats[sym])))

# MFE/MAE analysis
print("\n--- MFE/MAE Analysis ---")
for p in settled[:5]:
    print("  {} {} mfe={:.2f}% mae={:.2f}% final={:.2f}%".format(
        p.get("symbol","?"), p.get("direction","?"), 
        p.get("mfe_pct",0), p.get("mae_pct",0), p.get("final_pnl_pct",0)))

# === State History ===
spath = os.path.expanduser("~/.hermes/state.json")
if os.path.exists(spath):
    s = json.load(open(spath))
    hist = s.get("history", [])
    pos = s.get("positions", {})
    print("\n" + "=" * 60)
    print("POSITION STATE")
    print("=" * 60)
    print("Active positions: {}".format(len(pos)))
    for k, v in list(pos.items())[:5]:
        print("  {}: entry={} size={} pnl={}".format(k, v.get("entry_price"), v.get("size"), v.get("unrealized_pnl", 0)))
    print("History: {} trades".format(len(hist)))
    if hist:
        hwins = [h for h in hist if h.get("pnl", 0) > 0]
        hloss = [h for h in hist if h.get("pnl", 0) <= 0]
        print("Wins: {} | Losses: {} | WR: {:.1f}%".format(
            len(hwins), len(hloss), len(hwins)/len(hist)*100 if hist else 0))
