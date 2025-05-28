import random
from config import PAYOUT_RATES

def generate_bets(players: dict, round_index: int) -> dict:
    """
    根据玩家状态和标签生成本局投注计划。
    players: dict[str, Player]，玩家标签对象字典
    round_index: 当前局数，从1开始。
    返回：dict[str, dict[int, int]]，玩家ID对应的下注区域及金额字典。
    """

    bets = {}

    for pid, player in players.items():
        # 参与状态判定
        if round_index == 1:
            player.is_active = random.random() < 0.3
            if not player.is_active:
                player.consecutive_missed = 1
        else:
            if player.is_active:
                if random.random() > 0.85:
                    player.is_active = False
                    player.consecutive_missed = 1
            else:
                p_restore = min(1.0, 0.1 + 0.05 * player.consecutive_missed)
                if random.random() < p_restore:
                    player.is_active = True
                    player.consecutive_missed = 0
                else:
                    player.consecutive_missed += 1

        if not player.is_active:
            continue

        total_amount = random.randint(int(player.amount_scale * 0.8), int(player.amount_scale * 1.2))
        min_area, max_area = player.area_range        
        chosen_num = random.randint(min_area, max_area)
        chosen_areas = random.sample(range(1, 9), chosen_num)

        # 按赔率倒数计算基础权重
        base_weights = [1 / PAYOUT_RATES[area] for area in chosen_areas]
        total_weight = sum(base_weights)
        norm_weights = [w / total_weight for w in base_weights]

        # 将投注总额转化为 500 单元数分配
        total_units = total_amount // 500
        unit_allocations = [0] * chosen_num

        for _ in range(total_units):
            r = random.random()
            acc = 0.0
            for i, w in enumerate(norm_weights):
                acc += w
                if r <= acc:
                    unit_allocations[i] += 1
                    break

        final_bets = {}
        for area, units in zip(chosen_areas, unit_allocations):
            if units > 0:
                final_bets[area] = units * 500

        bets[pid] = final_bets

    return bets
