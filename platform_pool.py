# platform_pool.py

"""
平台水池管理模块：
- 记录平台盈亏累积值（抽水后下注金额流入，中奖金额流出）
- 根据水位线调整目标 RTP（实现动态放水 / 回收策略）
"""

from typing import List, Tuple

class PlatformPool:
    def __init__(self, initial_value: float = 5_000_000, tax_rate: float = 1.0):
        self.pool_value = initial_value
        self.tax_rate = tax_rate / 100.0  # 1% => 0.01
        self.history = []

        # 水位线：按从高水位到低排序
        self.rtp_thresholds: List[Tuple[float, float, float]] = [
            (1.20, 10_000_000, float("inf")),
            (1.10, 8_000_000, 10_000_000),
            (1.05, 6_000_000, 8_000_000),
            (1.00, 4_000_000, 6_000_000),
            (0.95, 2_000_000, 4_000_000),
            (0.90, 0, 2_000_000),
            (0.80, float("-inf"), 0),
        ]

    def inflow(self, bet_amount: float):
        """下注入池（抽水后）"""
        taxed = bet_amount * (1 - self.tax_rate)
        self.pool_value += taxed
        self.history.append(("in", taxed))

    def outflow(self, payout_amount: float):
        """派奖出池"""
        self.pool_value -= payout_amount
        self.history.append(("out", payout_amount))

    def get_current_rtp_target(self) -> float:
        """根据当前水位线返回 RTP 目标值"""
        for rtp, low, high in self.rtp_thresholds:
            if low <= self.pool_value < high:
                return rtp
        return 1.00  # fallback

    def get_pool_value(self) -> float:
        return self.pool_value

    def get_latest_deltas(self, n: int = 10):
        return self.history[-n:]
