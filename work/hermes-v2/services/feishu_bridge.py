"""Feishu Bot Bridge - connects V2 signals to V1's feishu_callback."""
import sys, os

class FeishuBridge:
    """Bridge to V1's feishu_callback for /analyze, /dag, /status commands."""

    def __init__(self):
        self.available = False
        self._handle_analyze = None
        self._handle_dag = None
        self._handle_status = None
        self._send_msg = None
        try:
            v1_path = '/home/ubuntu/scripts/agents'
            if v1_path not in sys.path:
                sys.path.insert(0, v1_path)
            from feishu_callback import handle_analyze, handle_dag, handle_status, send_msg
            self._handle_analyze = handle_analyze
            self._handle_dag = handle_dag
            self._handle_status = handle_status
            self._send_msg = send_msg
            self.available = True
        except ImportError:
            pass

    def analyze(self, symbol, chat_id):
        """Run /分析 command for a symbol."""
        if not self.available:
            return 'Feishu bridge not available'
        try:
            return self._handle_analyze(symbol, chat_id)
        except Exception as e:
            return f'Analyze error: {e}'

    def dag(self, symbol, chat_id):
        """Run /dag command."""
        if not self.available:
            return 'Feishu bridge not available'
        try:
            return self._handle_dag(symbol, chat_id)
        except Exception as e:
            return f'DAG error: {e}'

    def status(self, chat_id):
        """Run /status command."""
        if not self.available:
            return 'Feishu bridge not available'
        try:
            return self._handle_status(chat_id)
        except Exception as e:
            return f'Status error: {e}'

    def send(self, chat_id, text):
        """Send message to Feishu chat."""
        if not self.available:
            return
        try:
            self._send_msg(chat_id, text)
        except Exception:
            pass
