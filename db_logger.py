# db_logger.py

"""
对局与玩家日志记录模块

包括两张表：
1. round_log：以对局为主视角，记录平台维度的投注与盈利信息
2. player_log：以玩家为主视角，记录每个玩家的下注与返奖信息
"""

from config import MEMORY_WINDOW  # N 局窗口长度
from typing import Dict, List

# 对局日志（平台视角）
round_log: List[Dict] = []

# 玩家日志（个人视角）
player_log: List[Dict] = []


def log_round_summary(
    round_id: int,
    player_bets: Dict[str, Dict[int, float]],
    area_totals: Dict[int, float],
    winning_areas: List[int],
    total_bet: float,
    total_payout: float
):
    """
    记录单局平台级别数据：投注分布、开奖结果、盈利情况
    """
    round_log.append({
        "round_id": round_id,
        "player_bets": player_bets,
        "area_total_bets": area_totals,
        "winning_areas": winning_areas,
        "total_bet": total_bet,
        "total_payout": total_payout,
        "platform_profit": total_bet - total_payout
    })


def log_player_detail(
    round_id: int,
    player_id: str,
    area_bets: Dict[int, float],
    total_bet: float,
    payout: float
):
    net_profit = payout - total_bet

    # 获取该玩家近 MEMORY_WINDOW 局投注额
    recent_bets = [
        log["total_bet"] for log in player_log
        if log["player_id"] == player_id and log["total_bet"] > 0
    ][-MEMORY_WINDOW:]

    if recent_bets:
        avg_bet_recent = sum(recent_bets) / len(recent_bets)
        memory_profit = net_profit / avg_bet_recent if avg_bet_recent > 0 else 0.0
    else:
        memory_profit = 0.0

    player_log.append({
        "round_id": round_id,
        "player_id": player_id,
        "area_bets": area_bets,
        "total_bet": total_bet,
        "payout": payout,
        "net_profit": net_profit,
        "memory_profit": memory_profit
    })
