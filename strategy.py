# strategy.py

"""
控奖策略模块：
- 接收结构指标数据（由 metrics_engine 提供）
- 可选接入评分信息（由 scoring_engine 提供）
- 按策略逻辑选出最终开奖结果结构

🗃️ evaluator.py 模块已废弃，功能已完整拆分入 metrics_engine / scoring_engine / strategy
"""

from typing import List, Dict, Tuple
from config import PAYOUT_RATES

# --- [主函数] 根据结构指标结果选择最终开奖结果 ---
def select_structure(
    results: List[Dict],
    current_bets: Dict[str, Dict[int, float]],
    *,
    std_bounds: Tuple[float, float],
    base_std: float
) -> Dict:
    rtp_std_low, rtp_std_high = std_bounds

    # --- 情况一：有结构落入置信区间内 ---
    filtered = [r for r in results if r.get("within_confidence")]
    if filtered:
        ranked = sorted(
            filtered,
            key=lambda r: r.get("memory_effect", 0.0)
        )
        return ranked[0]
    
    # --- 情况二：没有结构落入置信区间 ---
    acceptable = []

    for r in results:
        payout = sum(
            amount * PAYOUT_RATES[area]
            for pid, bets in current_bets.items()
            for area, amount in bets.items()
            if area in r["winning_areas"]
        )
        total_bet = sum(sum(bets.values()) for bets in current_bets.values())
        rtp = payout / total_bet if total_bet > 0 else 0

        if rtp <= 2:  # ✅ 仍保留平台最多亏一倍的限制
            acceptable.append(r)

    if acceptable:
        # ✅ 在可接受的结构中选 std 最小的
        best = min(acceptable, key=lambda r: r["std"])
    else:
        # 若所有都超过2倍赔付上限，才在全局中选 std 最小
        best = min(results, key=lambda r: r["std"])

    return best
