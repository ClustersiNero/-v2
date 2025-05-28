import streamlit as st
import random
from player_profiles import initialize_players, PlayerStats
from platform_pool import PlatformPool
from config import ROUND_TOTAL_DURATION, BETTING_DURATION, WAITING_DURATION

# ✅ 控奖系统核心 Session 状态初始化函数
def initialize_session_state():
    if "sim_players" not in st.session_state:
        st.session_state.sim_players = initialize_players()
    if "stat_players" not in st.session_state:
        st.session_state.stat_players = {pid: PlayerStats() for pid in st.session_state.sim_players.keys()}
    if "rtp_history" not in st.session_state:
        st.session_state.rtp_history = {}
    if "round_id" not in st.session_state:
        st.session_state.round_id = 1
    if "time_to_next_round" not in st.session_state:
        st.session_state.time_to_next_round = ROUND_TOTAL_DURATION
    if "countdown_bet" not in st.session_state:
        st.session_state.countdown_bet = BETTING_DURATION
    if "countdown_result" not in st.session_state:
        st.session_state.countdown_result = WAITING_DURATION
    if "current_bets" not in st.session_state:
        st.session_state.current_bets = {}
    if "running" not in st.session_state:
        st.session_state.running = False
    if "online_base" not in st.session_state:
        st.session_state.online_base = random.randint(65, 75)
    if "final_outcome" not in st.session_state:
        st.session_state.final_outcome = None
    if "forced_outcome" not in st.session_state:
        st.session_state.forced_outcome = None
    if "structure_result_cache" not in st.session_state:
        st.session_state.structure_result_cache = None
    if "partial_bets" not in st.session_state:
        st.session_state.partial_bets = {}
    if "has_started" not in st.session_state:
        st.session_state.has_started = False
    if "platform_pool" not in st.session_state:
        st.session_state.platform_pool = PlatformPool()

# ✅ 策略参数维护函数：分离 UI 和 session 初始化，便于日后统一管理
def ensure_param_defaults():
    if "debug_speed" not in st.session_state:
        st.session_state.debug_speed = 1.0  # 默认 1 倍速
    if "target_rtp" not in st.session_state:
        st.session_state.target_rtp = 0.98  # 默认目标 RTP
    if "confidence_level" not in st.session_state:
        st.session_state.confidence_level = 0.95  # 默认置信度