"""Tracker daemon: reads signal log, builds stats."""
import json, os, time

class TrackerDaemon:
    def __init__(self, log_dir=None):
        self.log_dir = log_dir or os.path.expanduser('~/hermes-v2/logs')
        self.output = os.path.join(self.log_dir, 'pipeline_tracker.json')
        self.signal_log = os.path.join(self.log_dir, 'v2_signals.jsonl')

    def read_signals(self):
        entries = []
        if os.path.exists(self.signal_log):
            with open(self.signal_log) as f:
                for line in f:
                    if line.strip():
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return entries

    def build_stats(self, entries):
        symbols = {}
        indicators = {}
        for e in entries:
            sym = e.get('symbol', '?')
            if sym not in symbols:
                symbols[sym] = {'count': 0, 'total_score': 0, 'directions': {}}
            symbols[sym]['count'] += 1
            symbols[sym]['total_score'] += abs(e.get('score', 0))
            d = e.get('direction', '?')
            symbols[sym]['directions'][d] = symbols[sym]['directions'].get(d, 0) + 1
            for k in e.get('details', {}):
                indicators[k] = indicators.get(k, 0) + 1
        return symbols, indicators

    def run_once(self):
        entries = self.read_signals()
        symbols, indicators = self.build_stats(entries)
        result = {
            'ts': time.time(),
            'iso': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_signals': len(entries),
            'unique_coins': len(symbols),
            'top_coins': [(s, v['count'], v['total_score']//max(1,v['count'])) 
                         for s, v in sorted(symbols.items(), key=lambda x: -x[1]['count'])[:10]],
            'top_indicators': sorted(indicators.items(), key=lambda x: -x[1])[:15],
        }
        os.makedirs(os.path.dirname(self.output), exist_ok=True)
        with open(self.output, 'w') as f:
            json.dump(result, f, indent=2)
        return result
