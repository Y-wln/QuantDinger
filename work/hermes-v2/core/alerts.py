"""Alerting: Feishu webhook + file log."""
import time, json, os, urllib.request

class Alerts:
    def __init__(self, webhook_url=None, log_dir=None):
        self.webhook = webhook_url or os.environ.get('FEISHU_WEBHOOK', '')
        self.log_dir = log_dir or os.path.expanduser('~/hermes-v2/logs')
        os.makedirs(self.log_dir, exist_ok=True)

    def send(self, title, body, level='info'):
        """Send alert to Feishu and local log."""
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{ts}] [{level.upper()}] {title}: {body}"
        log_file = os.path.join(self.log_dir, f"alerts_{time.strftime('%Y%m%d')}.log")
        with open(log_file, 'a') as f:
            f.write(log_line + '\n')
        if self.webhook:
            try:
                payload = json.dumps({
                    'msg_type': 'text',
                    'content': {'text': f"{title}\n{body}"}
                }).encode()
                req = urllib.request.Request(self.webhook, data=payload,
                    headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass

    def signal(self, symbol, direction, score, price, reasons):
        """Format and send trading signal."""
        emoji = '🟢' if direction == 'long' else '🔴'
        body = f"{emoji} {symbol} {direction.upper()} | Score:{score} | ${price}\n" + '\n'.join(f"  {r}" for r in reasons)
        self.send(f"Signal: {symbol}", body, 'signal')

    def error(self, module, msg):
        self.send(f"ERROR: {module}", msg, 'error')

    def info(self, module, msg):
        self.send(f"INFO: {module}", msg, 'info')
