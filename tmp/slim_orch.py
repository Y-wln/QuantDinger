import sys, os
sys.path.insert(0, '/home/ubuntu/scripts/agents')

# ====== 1. Slim agent_orchestrator.py ======
with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove market/sentiment agent imports
content = content.replace("""
    def _init_agents(self):
        from agent_market import MarketAgent
        from agent_technical import TechnicalAgent
        from agent_sentiment import SentimentAgent
        from agent_position import PositionAgent
        self.market = MarketAgent()
        self.technical = TechnicalAgent()
        self.sentiment = SentimentAgent()
        self.position = PositionAgent()
        self.position.max_positions = MAX_POSITIONS""", 
"""
    def _init_agents(self):
        from agent_technical import TechnicalAgent
        from agent_position import PositionAgent
        self.technical = TechnicalAgent()
        self.position = PositionAgent()
        self.position.max_positions = MAX_POSITIONS""")

# Replace self.market.get_klines -> fetch_klines
content = content.replace('self.market.get_klines(sym,', 'fetch_klines(sym,')
content = content.replace('self.market.get_klines("BTCUSDT"', 'fetch_klines("BTCUSDT"')

# Replace self.market.get_price -> fetch_price
content = content.replace('self.market.get_price(sym)', 'fetch_price(sym)')

# The orchestrator no longer uses sentiment agent directly (it uses fetch_fear_greed)
# Remove any remaining self.sentiment references
content = content.replace('self.sentiment.get_fng_score()', '0')  # not used in current code

# Add hermes_core imports for fetch_klines/fetch_price directly
old_fetch_import = '    fetch_price, atr, fetch_taker_volume, fetch_long_short_ratio,'
new_fetch_import = '    fetch_price, fetch_klines, atr, fetch_taker_volume, fetch_long_short_ratio,'
content = content.replace(old_fetch_import, new_fetch_import)

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/agent_orchestrator.py', doraise=True)
print('agent_orchestrator.py: slimmed OK')

# ====== 2. Delete dead files ======
dead_files = [
    '/home/ubuntu/scripts/agents/agent_market.py',
    '/home/ubuntu/scripts/agents/agent_sentiment.py',
    '/home/ubuntu/scripts/agents/liq_collector.py',
    '/home/ubuntu/scripts/agents/liq_heatmap.py',
    '/home/ubuntu/scripts/agents/smart_money.py',
]
for f in dead_files:
    if os.path.exists(f):
        os.remove(f)
        print(f'Deleted: {f}')

# Clear pyc cache
cache_dir = '/home/ubuntu/scripts/agents/__pycache__'
for f in os.listdir(cache_dir):
    if any(d in f for d in ['agent_market','agent_sentiment','liq_collector','liq_heatmap','smart_money']):
        os.remove(os.path.join(cache_dir, f))
        print(f'Removed cache: {f}')

print('\nDone! Removed 5 dead files, slimmed orchestrator')
