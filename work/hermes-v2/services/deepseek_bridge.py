"""DeepSeek AI Bridge - calls V1's call_deepseek for coin analysis."""
import sys

class DeepSeekBridge:
    """Bridge to V1's DeepSeek AI analysis."""

    def __init__(self):
        self.available = False
        self._call = None
        try:
            v1_path = '/home/ubuntu/scripts/agents'
            if v1_path not in sys.path:
                sys.path.insert(0, v1_path)
            from hermes_core import call_deepseek
            self._call = call_deepseek
            self.available = True
        except ImportError:
            pass

    def analyze(self, system_prompt, user_prompt, max_tokens=500):
        """Call DeepSeek for analysis. Returns text response or None."""
        if not self.available:
            return None
        try:
            return self._call(system_prompt, user_prompt, max_tokens)
        except Exception:
            return None

    def analyze_coin(self, symbol, price, indicators):
        """Analyze a coin with indicator context. Returns AI report or None."""
        if not self.available:
            return None

        system = "你是加密货币交易分析专家。根据指标给出简洁的多空判断和操作建议。"
        user = f"分析 {symbol} 当前价格 ${price}\n指标:\n"
        for k, v in list(indicators.items())[:15]:
            user += f"- {v}\n"
        user += "\n请给出: 方向(做多/做空/观望), 评分(1-100), 置信度, 3条理由, 止损建议"

        return self.analyze(system, user, max_tokens=400)
