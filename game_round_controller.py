from betting_input import generate_bets
from config import PAYOUT_RATES, ROUND_TOTAL_DURATION, BETTING_DURATION, STD_THRESHOLD, ANIMATION_DURATION
from score_engine import simulate_structure_metrics, simulate_structure_memory_effect  
from strategy import select_structure
import random
import pandas as pd
from enum import Enum, auto
import streamlit as st
from db_logger import log_player_detail

# ✅ 游戏阶段枚举，用于结构化替代 time_to_next_round 魔法判断
class GamePhase(Enum):
    BETTING = auto()
    WAITING = auto()
    ANIMATION = auto()
    SETTLED = auto()

class GameRoundController:
    """
    控制单轮对局的控制器类，封装下注生成、结构模拟、开奖与结算。

    使用三段控奖结构：
    1. simulate_structure_metrics：结构级指标生成（STD、命中等）
    2. score_structure：策略评分（玩家状态、平台策略）
    3. select_structure：结构筛选与开奖决策
    """
    def __init__(self, state):
        self.state = state
        self.round_id = state["round_id"]
        self.sim_players = state["sim_players"]
        self.stat_players = state["stat_players"]
        self.target_rtp = state.get("target_rtp", 0.98)
        self.confidence_level = state.get("confidence_level", 0.95)

    def get_current_phase(self) -> GamePhase:
        t = self.state["time_to_next_round"]
        if t > (ROUND_TOTAL_DURATION - BETTING_DURATION):
            return GamePhase.BETTING
        elif t > ANIMATION_DURATION:
            return GamePhase.WAITING
        elif t > 0:
            return GamePhase.ANIMATION
        else:
            return GamePhase.SETTLED

    def initialize_bets(self):
        """下注阶段初始化下注节奏与计划"""
        self.state["partial_bets"] = generate_bets(self.sim_players, self.round_id)

        for pid, bets in self.state["partial_bets"].items():
            scheduled_seconds = []
            bet_times = random.randint(1, BETTING_DURATION)

            # ✅ 用 set 去重，避免重复下注时间
            while len(scheduled_seconds) < bet_times:
                sec = int(random.gauss(mu=BETTING_DURATION * 0.75, sigma=max(1, BETTING_DURATION / 6)))
                if 1 <= sec <= BETTING_DURATION and sec not in scheduled_seconds:
                    scheduled_seconds.append(sec)

            scheduled_seconds.sort()
            self.state.setdefault("bet_schedule", {})
            self.state["bet_schedule"][pid] = scheduled_seconds

        self.evaluate_structures()

    def tick_betting_phase(self):
        """下注阶段每秒推进节奏（支持倍速）"""
        second_passed = BETTING_DURATION - self.state["countdown_bet"]
        for pid, full_bet in self.state["partial_bets"].items():
            scheduled_times = self.state.get("bet_schedule", {}).get(pid, [])
            if second_passed in scheduled_times:
                self.state["current_bets"].setdefault(pid, {})
                for area, total_amount in full_bet.items():
                    self.state["current_bets"][pid][area] = total_amount

        self.evaluate_structures()
        self.state["countdown_bet"] -= 1

    def evaluate_structures(self):
        results, std_analysis_data, std_bounds, sample_size = simulate_structure_metrics(
            self.stat_players,
            self.state["current_bets"],
            confidence_level=self.confidence_level,
            base_std=STD_THRESHOLD
        )

        # ✅ 新增：提取玩家充值额度（传给 memory_effect 模块）
        player_recharges = {
            pid: p.recharge_amount
            for pid, p in st.session_state.sim_players.items()
        }

        player_recharges = {
            pid: p.recharge_amount
            for pid, p in st.session_state.sim_players.items()
        }

        memory_effects = simulate_structure_memory_effect(
            self.stat_players,
            self.state["current_bets"],
            player_recharges,
            round_id=self.round_id
        )


        # 合并 memory_effect 到结构指标中
        for struct in results:
            match = next((m for m in memory_effects if m["winning_areas"] == struct["winning_areas"]), None)
            if match:
                struct["memory_effect"] = match["memory_effect"]

        self.state["structure_result_cache"] = {
            "all_structures": results,
            "std_analysis": std_analysis_data,
            "std_bounds": std_bounds,
            "sample_size": sample_size
        }

    def finalize_outcome(self):
        """开奖：优先强控，否则使用策略选择结构"""
        if self.state["forced_outcome"]:
            self.state["final_outcome"] = self.state["forced_outcome"]
        else:
            rtp_target = self.state["platform_pool"].get_current_rtp_target()
            outcome = select_structure(
                self.state["structure_result_cache"]["all_structures"],
                self.state["current_bets"],
                std_bounds=self.state["structure_result_cache"]["std_bounds"],
                base_std=rtp_target  # ✅ 由水池决定的动态 RTP 目标
            )
            self.state["final_outcome"] = outcome

    def settle(self):
        """结算：计算玩家 RTP 与回收，并同步水池入出账"""
        winning_areas = self.state["final_outcome"]["winning_areas"]
        for pid, bets in self.state["current_bets"].items():
            bet_sum = sum(bets.values())
            payout = sum(v * PAYOUT_RATES[a] for a, v in bets.items() if a in winning_areas)

            # ✅ 统一在结算阶段计入水池
            self.state["platform_pool"].inflow(bet_sum)
            self.state["platform_pool"].outflow(payout)

            self.stat_players[pid].update(bet_sum, payout)
            rtp = self.stat_players[pid].rtp()
            self.state["rtp_history"].setdefault(pid, []).append(rtp)

            log_player_detail(
            round_id=self.round_id,
            player_id=pid,
            area_bets=bets,
            total_bet=bet_sum,
            payout=payout
        )

    def tick(self):
        if self.state["time_to_next_round"] > (ROUND_TOTAL_DURATION - BETTING_DURATION):
            if self.state["countdown_bet"] == BETTING_DURATION:
                self.initialize_bets()
            self.tick_betting_phase()
        elif self.state["time_to_next_round"] > ANIMATION_DURATION:
            self.state["countdown_result"] -= 1
        elif self.state["time_to_next_round"] == ANIMATION_DURATION:
            self.finalize_outcome()
        elif self.state["time_to_next_round"] == 0:
            self.settle()
            self.state["running"] = False

        self.state["time_to_next_round"] -= 1

    def get_visual_context(self):
        """UI 展示：构建结构柱状图、推荐结构表格、高亮区域等上下文"""
        structure_sums = {i: 0 for i in range(1, 9)}
        for bets in self.state["current_bets"].values():
            for area, amt in bets.items():
                if area in structure_sums:
                    structure_sums[area] += amt

        highlight_areas = set()
        if self.state.get("final_outcome"):
            highlight_areas = set(self.state["final_outcome"].get("winning_areas", []))
        elif self.state.get("structure_result_cache"):
            for r in self.state["structure_result_cache"].get("all_structures", []):
                if r.get("within_confidence"):
                    highlight_areas.update(r.get("winning_areas", []))

        forced_areas = set(self.state["forced_outcome"]["winning_areas"]) if self.state.get("forced_outcome") else None

        table_df = pd.DataFrame(self.state.get("structure_result_cache", {}).get("all_structures", []))

        return {
            "structure_sums": structure_sums,
            "highlight_areas": highlight_areas,
            "forced_areas": forced_areas,
            "table_df": table_df
        }
