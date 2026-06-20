"""DAG Consensus V2: multi-indicator voting + fast indicator gate (leading_confirm)."""
class DAGConsensus:
    def __init__(self):
        self.min_fast_votes = 2  # must have 2+ fast votes to pass
        self.min_votes = 2

    def leading_confirm(self, signal, cvd_1m=None, orderbook_imb=None, tape_pressure=None):
        """V1-style fast indicator gate: 1mCVD + orderbook + tape >= 2 votes.
        Returns (passed, fast_votes, reasons)."""
        direction = signal.get('direction', 'neutral')
        score = signal.get('score', 0)
        fast_votes = 0
        fast_reasons = []
        reasons = []

        # 1. 1m CVD vote
        if cvd_1m is not None:
            if direction == 'long' and cvd_1m > 7:
                fast_votes += 1
                fast_reasons.append(f'1mCVD:{int(cvd_1m)}%')
            elif direction == 'short' and cvd_1m < -7:
                fast_votes += 1
                fast_reasons.append(f'1mCVD:{int(cvd_1m)}%')
            elif (direction == 'long' and cvd_1m < -8) or (direction == 'short' and cvd_1m > 8):
                fast_votes -= 1
                reasons.append('1mCVD反向-1票')

        # 2. Orderbook vote
        if orderbook_imb is not None:
            if direction == 'long' and orderbook_imb > 8:
                fast_votes += 1
                fast_reasons.append(f'盘口偏买:{int(orderbook_imb)}%')
            elif direction == 'short' and orderbook_imb < -8:
                fast_votes += 1
                fast_reasons.append(f'盘口偏卖:{int(orderbook_imb)}%')
            elif (direction == 'long' and orderbook_imb < -10) or (direction == 'short' and orderbook_imb > 10):
                fast_votes -= 1
                reasons.append('盘口反向-1票')

        # 3. Tape pressure vote
        if tape_pressure is not None:
            if (direction == 'long' and tape_pressure > 0.55) or (direction == 'short' and tape_pressure < 0.45):
                fast_votes += 1
                fast_reasons.append(f'tape{"偏买" if tape_pressure > 0.55 else "偏卖"}')
            elif (direction == 'long' and tape_pressure < 0.4) or (direction == 'short' and tape_pressure > 0.6):
                fast_votes -= 1
                reasons.append('tape反向-1票')

        # Gate logic
        if fast_votes >= 3:
            return True, fast_votes, fast_reasons + reasons
        elif fast_votes >= 2 and abs(score) >= self.threshold if hasattr(self, 'threshold') else 25:
            return True, fast_votes, fast_reasons + reasons
        elif fast_votes == 1 and abs(score) >= 35:
            return True, fast_votes, fast_reasons + reasons
        else:
            return False, fast_votes, [f'快指标不足({fast_votes}<2且评分<35)']

    def validate(self, signal):
        """Full DAG validation: indicator families + structure check."""
        details = signal.get('details', {})
        leading = signal.get('leading_signals', [])
        score = signal.get('score', 0)
        direction = signal.get('direction', 'neutral')

        votes = {'bullish': 0, 'bearish': 0}
        voter_map = {
            'bb1h': 'bb', 'cvd': 'cvd', 'cvd_accel': 'cvd', 'cv5': 'cvd',
            'ob': 'orderbook', 'smc': 'smc', 'rsi': 'rsi', 'rsi_div': 'rsi',
            'macd': 'macd', 'st4': 'supertrend', 'struct': 'structure',
            'momentum': 'momentum', 'vol_surge': 'volume', 'fng': 'sentiment',
            'fr': 'funding', 'regime': 'regime', 'engulfing': 'candles',
            'hvn': 'hvn',
        }

        voted_families = set()
        for key, value in details.items():
            family = 'other'
            for prefix, fam in voter_map.items():
                if key.startswith(prefix):
                    family = fam; break
            if family in voted_families:
                continue
            voted_families.add(family)
            if isinstance(value, str):
                if value.startswith('+'): votes['bullish'] += 1
                elif value.startswith('-'): votes['bearish'] += 1

        leading_count = len(leading)

        if direction == 'long':
            my_votes = votes['bullish']
            opp_votes = votes['bearish']
        else:
            my_votes = votes['bearish']
            opp_votes = votes['bullish']

        consensus_score = my_votes - opp_votes

        if my_votes < self.min_votes:
            return False, f'投票不足({my_votes}<{self.min_votes})', consensus_score

        if leading_count < 2 and abs(score) < 35:
            return False, f'领先信号不足({leading_count}<2且评分<35)', consensus_score

        if opp_votes > my_votes * 0.6:
            return False, f'反对票太多({opp_votes}/{my_votes})', consensus_score

        return True, f'共识通过({my_votes}票,{leading_count}领先)', consensus_score

    def filter_signals(self, signals):
        passed = []
        blocked = []
        for sig in signals:
            ok, reason, cs = self.validate(sig)
            sig['dag_consensus'] = cs
            sig['dag_reason'] = reason
            if ok: passed.append(sig)
            else: blocked.append((sig, reason))
        return passed, blocked
