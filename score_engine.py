# scoring_engine.py

"""
结构评分模块：
- 接收结构及其命中区域信息
- 结合玩家状态与上下文，对结构进行多维打分（如：玩家亏损、追击中、首登场等）
- 输出用于排序的评分值
"""

from typing import Dict, Any, List
from config import PAYOUT_RATES, WINNING_STRUCTURES, STD_THRESHOLD, CONFIDENCE_LEVEL, MINIMUM_BET_THRESHOLD, MEMORY_WINDOW, MEMORY_DECAY_ALPHA
from player_profiles import PlayerStats
from metrics_engine import calculate_weighted_std, compute_dynamic_std_confidence_interval, calculate_memory_attitude
from copy import deepcopy
from db_logger import player_log
import math




# --- [主函数] 控奖结构打分 ---
def score_structure(
    winning_areas: list[int],
    current_bets: Dict[str, Dict[int, float]],
    player_states: Dict[str, Dict[str, Any]],
    session_context: Dict[str, Any]
) -> float:
    """
    当前版本已不使用评分逻辑。此函数保留为空，待后续策略定义具体用途。
    """
    return 0.0

# --- 模拟结构指标 ---
def simulate_structure_metrics(
    current_players: Dict[str, PlayerStats],
    current_bets: Dict[str, Dict[int, float]],
    *,
    confidence_level: float = CONFIDENCE_LEVEL,
    base_std: float = STD_THRESHOLD
):
    """
    输入：玩家状态 + 当前下注
    输出：每个结构的标准差、权重、命中情况等结构级分析数据
    """
    eligible_players = [
        current_players[pid] for pid, bets in current_bets.items()
        if sum(bets.values()) >= MINIMUM_BET_THRESHOLD
    ]
    rtp_std_low, rtp_std_high = compute_dynamic_std_confidence_interval(
        base_std, confidence_level, len(eligible_players)
    )

    results = []
    std_analysis_data = []

    for structure in deepcopy(WINNING_STRUCTURES):
        winning_areas = structure["areas"]
        weight = structure["weight"]
        simulated_attitudes = []
        simulated_players = deepcopy(current_players)

        # 模拟结算
        for player_id, bets in current_bets.items():
            payout = sum(
                amount * PAYOUT_RATES[area]
                for area, amount in bets.items()
                if area in winning_areas
            )
            simulated_players[player_id].update(sum(bets.values()), payout)

        filtered_players = {
            pid: simulated_players[pid]
            for pid, bets in current_bets.items()
            if sum(bets.values()) >= MINIMUM_BET_THRESHOLD
        }
        std_value, std_details = calculate_weighted_std(filtered_players, return_details=True)

        results.append({
            "winning_areas": winning_areas,
            "std": std_value,
            "weight": weight,
            "within_confidence": rtp_std_low <= std_value <= rtp_std_high
        })

        std_analysis_data.append({
            "winning_areas": winning_areas,
            "std": std_value,
            "details": std_details
        })

    return results, std_analysis_data, (rtp_std_low, rtp_std_high), len(eligible_players)

def simulate_structure_memory_effect(
    current_players: Dict[str, PlayerStats],
    current_bets: Dict[str, Dict[int, float]],
    player_recharges: Dict[str, float],
    round_id: int
) -> List[Dict]:
    """
    对每个结构模拟其对充值玩家的“态势缓冲”效果（记忆态势值的振幅增量）。
    """
    results = []

    for structure in deepcopy(WINNING_STRUCTURES):
        winning_areas = structure["areas"]
        weight = structure["weight"]

        simulated_attitudes = []
        affected_players = []

        memory_effect = 0.0   # ✅ 请在这里补上这行，防止结构无玩家时未赋值

        for pid, stats in current_players.items():
            # ✅ 该玩家必须在当前局有下注
            if pid not in current_bets or sum(current_bets[pid].values()) == 0:
                continue

            # ✅ 条件筛选：充值 + 当前态势值极端
            recharge = player_recharges.get(pid, 0.0)
            current_attitude = calculate_memory_attitude(pid, round_id)

            if recharge <= 0:
            # or (-0.2 < current_attitude < 0.2):
                continue
            
            # ✅ 获取当前记忆态势值
            current_attitude = calculate_memory_attitude(pid, round_id)

            # ✅ 模拟该结构下该玩家是否中奖
            area_bets = current_bets[pid]
            bet_total = sum(area_bets.values())
            payout_simulated = sum(
                amount * PAYOUT_RATES[area]
                for area, amount in area_bets.items()
                if area in winning_areas
            )
            net_profit_simulated = payout_simulated - bet_total

            # ✅ 获取历史 MEMORY_WINDOW 条真实投注记忆
            recent_memory = []
            for log in reversed(player_log):
                if log["player_id"] == pid and log["round_id"] < round_id and log["total_bet"] > 0:
                    if "memory_profit" in log:
                        recent_memory.append(log["memory_profit"])
                    if len(recent_memory) == MEMORY_WINDOW:
                        break
            recent_memory.reverse()  # 最新在前

            # ✅ 同时收集 recent_memory 和 recent_bets，用于计算平均投注
            recent_memory = []
            recent_bets = []
            for log in reversed(player_log):
                if log["player_id"] == pid and log["round_id"] < round_id and log["total_bet"] > 0:
                    if "memory_profit" in log:
                        recent_memory.append(log["memory_profit"])
                    recent_bets.append(log["total_bet"])
                    if len(recent_bets) == MEMORY_WINDOW:
                        break
                    
            # ✅ 计算平均投注额（基于参与局）
            recent_memory.reverse()
            recent_bets.reverse()
            if recent_bets:
                avg_bet = sum(recent_bets) / len(recent_bets)
                simulated_memory_profit = net_profit_simulated / avg_bet if avg_bet > 0 else 0.0
            else:
                simulated_memory_profit = 0.0

            # ✅ 构造模拟后的记忆列表
            combined_memory = [simulated_memory_profit] + recent_memory

            # ✅ 按指数衰减生成模拟态势值
            simulated_attitude = 0.0
            for i, mem in enumerate(combined_memory[:MEMORY_WINDOW]):
                weight_decay = math.exp(-MEMORY_DECAY_ALPHA * i)
                simulated_attitude += mem * weight_decay

            # ✅ 收集模拟态势值
            simulated_attitudes.append(simulated_attitude)
            affected_players.append(pid)

        # ✅ 所有玩家处理完成后，计算结构的记忆标准差效果
        weights = [player_recharges.get(pid, 0.0) for pid in affected_players]
        total_weight = sum(weights)
        
        if total_weight > 0:
            weighted_mean = sum(w * x for w, x in zip(weights, simulated_attitudes)) / total_weight
            weighted_variance = sum(w * (x - weighted_mean) ** 2 for w, x in zip(weights, simulated_attitudes)) / total_weight
            memory_effect = weighted_variance ** 0.5
        else:
            memory_effect = 0.0


        results.append({
            "winning_areas": winning_areas,
            "weight": weight,
            "memory_effect": memory_effect,
            "affected_players": affected_players
        })



    return results
