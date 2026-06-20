with open('/home/ubuntu/scripts/agents/feishu_callback.py', 'r') as f:
    content = f.read()

# 1. Update ai_route prompt to include entry analysis
old_prompt = '规则:\n- 问某个币的分析/行情/走势/怎么看 → action:analyze, symbol:币种(如BTC/ETH/SOL,只取币代码,不要-USDT)\n- 问妖币/扫描/高波动/有什么机会/推荐 → action:scan'
new_prompt = '规则:\n- 问能不能做多/做空/进场/入场/现在能做/开仓 → action:entry, symbol:币种(如BTC/ETH/SOL)\n- 问某个币的分析/行情/走势/怎么看 → action:analyze, symbol:币种(如BTC/ETH/SOL,只取币代码,不要-USDT)\n- 问妖币/扫描/高波动/有什么机会/推荐 → action:scan'
content = content.replace(old_prompt, new_prompt)

# 2. Add handle_entry before handle_analyze
old_handle_analyze = '\ndef handle_analyze(sym, chat_id):'
new_entry_handler = '''
def handle_entry(sym, chat_id):
    try:
        from entry_report import entry_report
        send_msg(chat_id, '正在生成 ' + sym.upper() + ' 进场分析报告...')
        r = entry_report(sym.upper().strip())
        if not r:
            send_msg(chat_id, '分析失败，请稍后重试')
            return
        ts = time.strftime('%m/%d %H:%M')
        lines = []
        lines.append('**' + r['sym'] + ' 进场分析报告**')
        lines.append('分析时间: ' + ts)
        lines.append('价格: **$' + str(r['price']) + '**  |  EMA20: ' + str(r['e20']))
        lines.append('')
        sig_label = 'LONG' if r['signal']=='long' else ('SHORT' if r['signal']=='short' else 'WAIT')
        sig_color = '#2ecc71' if r['signal']=='long' else ('#e74c3c' if r['signal']=='short' else '#95a5a6')
        lines.append('综合评分: **' + str(r['score']) + '分** → ' + sig_label + ' (门槛' + str(r['params']['th']) + '分)')
        lines.append('')
        lines.append('维度评分:')
        for k, v in r['dims'].items():
            lines.append('  ' + k + ': ' + v)
        lines.append('')
        lines.append('ATR: ' + str(r['atr']) + '  |  SL: ' + str(r['sl']) + '  |  TP: ' + str(r['tp']))
        lines.append('')
        entry_status = 'OK' if r['entry_ok'] else 'HOLD'
        entry_icon = 'ready' if r['entry_ok'] else 'wait'
        lines.append('进场判断: **' + entry_status + '**')
        if r['entry_note']:
            lines.append(r['entry_note'])
        send_card(chat_id, r['sym'] + ' 进场分析', lines, sig_color)
    except Exception as e:
        send_msg(chat_id, '分析出错: ' + str(e))
        traceback.print_exc()

def handle_analyze(sym, chat_id):'''

content = content.replace(old_handle_analyze, new_entry_handler + old_handle_analyze)

# 3. Add entry routing in route_command
old_scan_route = "    if result['action'] == 'analyze':"
new_scan_route = "    if result['action'] == 'entry':\n        sym = result.get('symbol','BTC').upper().strip()\n        if sym and len(sym) >= 2:\n            handle_entry(sym, chat_id)\n        else:\n            handle_entry('BTC', chat_id)\n\n    elif result['action'] == 'analyze':"
content = content.replace(old_scan_route, new_scan_route)

with open('/home/ubuntu/scripts/agents/feishu_callback.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/feishu_callback.py', doraise=True)
print('feishu_callback updated with entry analysis')
