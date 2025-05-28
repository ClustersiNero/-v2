import random
import numpy as np

class Player:
    """
    模拟投注用虚拟玩家类，仅用于下注模拟，独立于核心算法标签体系。
    """

    # ✅ 四类标签映射表（行为解释参数）
    AMOUNT_SCALE_MAP = {'大R': 10000, '中R': 2000, '小R': 1000}
    AREA_RANGE_MAP = {'海投': (6, 8), '保守': (3, 5), '谨慎': (1, 2)}
    BET_FREQUENCY = {'高频': 10, '中频': 3, '低频': 1}
    REBET_PROBABILITY = {'高概率': 0.8, '低概率': 0.3, '零概率': 0.0}

    def __init__(self, uid):
        self.uid = uid

        # ✅ 标签生成
        self.bet_amount_class = random.choices(list(self.AMOUNT_SCALE_MAP.keys()), weights=[1, 2, 10], k=1)[0]
        self.bet_area_style = random.choices(list(self.AREA_RANGE_MAP.keys()), weights=[1, 6, 1], k=1)[0]
        self.bet_freq_class = random.choices(list(self.BET_FREQUENCY.keys()), weights=[3, 3, 1], k=1)[0]
        self.rebet_prob_class = random.choices(list(self.REBET_PROBABILITY.keys()), weights=[5, 3, 2], k=1)[0]

        # ✅ 映射参数赋值
        self.amount_scale = self.AMOUNT_SCALE_MAP[self.bet_amount_class]
        self.area_range = self.AREA_RANGE_MAP[self.bet_area_style]
        self.bet_freq_value = self.BET_FREQUENCY[self.bet_freq_class]
        self.rebet_prob = self.REBET_PROBABILITY[self.rebet_prob_class]

        # ✅ 充值额度（根据档位 + 截断对数分布 + 最小单位取整）
        if self.bet_amount_class == "大R":
            val = int(np.random.lognormal(mean=4, sigma=0.5))
            val = min(max(val, 100), 5000)
            self.recharge_amount = val // 100 * 100
        elif self.bet_amount_class == "中R":
            val = int(np.random.lognormal(mean=3, sigma=0.4))
            val = min(max(val, 30), 100)
            self.recharge_amount = val // 10 * 10
        else:  # 小R
            val = int(np.random.lognormal(mean=2, sigma=0.3))
            val = min(max(val, 0), 30)
            self.recharge_amount = val // 5 * 5

        # ✅ 其他运行时状态
        self.consecutive_missed = 0
        self.is_active = False


class PlayerStats:
    """
    控奖用的玩家 RTP 数据结构，跟下注行为无关。
    """
    def __init__(self):
        self.total_bet = 0
        self.total_return = 0

    def update(self, bet_amount, payout_amount):
        self.total_bet += bet_amount
        self.total_return += payout_amount

    def rtp(self):
        if self.total_bet == 0:
            return 1.0
        return self.total_return / self.total_bet


def initialize_players(num_players=200):
    """
    生成模拟投注用玩家列表，带虚拟标签与状态，方便下注模拟调用。
    """
    players = {}
    for i in range(1, num_players + 1):
        p = Player(uid=f'player_{i}')
        players[p.uid] = p
    return players
