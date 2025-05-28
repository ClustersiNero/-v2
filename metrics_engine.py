# metrics_engine.py

"""
结构级指标计算模块：
- 接收当前投注与玩家数据
- 遍历所有开奖结构
- 输出每个结构的标准差、样本详情、权重、命中情况等分析指标
"""

from typing import Dict
from config import MINIMUM_BET_THRESHOLD, TARGET_RTP, MEMORY_WINDOW, MEMORY_DECAY_ALPHA
from player_profiles import PlayerStats
from scipy.stats import norm
from db_logger import player_log  # 
import math
from math import isclose


# --- 动态置信区间计算 ---
def compute_dynamic_std_confidence_interval(base_std: float, confidence: float, sample_size: int):
    if sample_size <= 1:
        return 0.0, base_std
    z = norm.ppf(1 - (1 - confidence) / 2)
    margin = z * base_std / (sample_size ** 0.5)
    return 0.0, base_std + margin  # ✅ 左边固定为 0

# --- 加权 RTP 标准差计算 ---
def calculate_weighted_std(players: Dict[str, PlayerStats], return_details=False):
    eligible = [(pid, p) for pid, p in players.items() if p.total_bet >= MINIMUM_BET_THRESHOLD]
    total_weight = sum(p.total_bet for _, p in eligible)
    if total_weight == 0:
        if return_details:
            return 0, {"players": [], "target_rtp": TARGET_RTP, "weighted_variance": 0}
        return 0

    weighted_variance = sum(
        p.total_bet * (p.rtp() - TARGET_RTP) ** 2
        for _, p in eligible
    ) / total_weight
    std = math.sqrt(weighted_variance)

    if return_details:
        details = {
            "players": [
                {
                    "id": pid,
                    "bet": p.total_bet,
                    "return": p.total_return,
                    "rtp": p.rtp(),
                    "weight": p.total_bet / total_weight
                }
                for pid, p in eligible
            ],
            "target_rtp": TARGET_RTP,
            "weighted_variance": weighted_variance
        }
        return std, details

    return std

# --- 记忆盈利计算 ---
def generate_memory_profit(player_id: str, round_id: int) -> float:
    """
    计算玩家在某局的记忆盈利（记忆值）：
    = 当前局净收益 ÷ 近 MEMORY_WINDOW 局的平均投注额（仅统计有下注的局）

    - 若历史局数不足 MEMORY_WINDOW，则使用已有局数；
    - 若历史投注均为 0，返回 0.0；
    """
    # 当前局的日志记录
    current = next((
        log for log in player_log
        if log["player_id"] == player_id and log["round_id"] == round_id
    ), None)

    if current is None:
        return 0.0

    net_profit = current["net_profit"]

    # ✅ 正确回溯逻辑：向前查找满足 MEMORY_WINDOW 个非零投注局
    recent_bets = []
    for log in reversed(player_log):
        if log["player_id"] == player_id and log["round_id"] < round_id:
            if log["total_bet"] > 0:
                recent_bets.append(log["total_bet"])
            if len(recent_bets) == MEMORY_WINDOW:
                break

    if not recent_bets:
        return 0.0

    avg_bet = sum(recent_bets) / len(recent_bets)
    return net_profit / avg_bet if not isclose(avg_bet, 0.0) else 0.0

def calculate_memory_attitude(player_id: str, round_id: int) -> float:
    """
    根据历史记忆记录与指数衰减权重，生成当前的“记忆态势值”。

    公式：Attitude = Σ(memory_profit_i × exp(-α * i))
    - i 越小越靠近当前，越大越久远
    - 仅统计有投注的 MEMORY_WINDOW 条历史记录
    """
    # 严格回溯最近 MEMORY_WINDOW 条有投注的历史记录（按时间顺序）
    memory_list = []
    for log in reversed(player_log):
        if log["player_id"] == player_id and log["round_id"] < round_id and log["total_bet"] > 0:
            if "memory_profit" in log:
                memory_list.append(log["memory_profit"])
            if len(memory_list) == MEMORY_WINDOW:
                break
    memory_list.reverse()  # i = 0 表示最新（当前局），越大越久远

    # 加权求和
    attitude = 0.0
    for i, m in enumerate(memory_list):
        weight = math.exp(-MEMORY_DECAY_ALPHA * i)
        attitude += m * weight

    return attitude
