import streamlit as st
import pandas as pd
import time
from state_manager import initialize_session_state, ensure_param_defaults
from game_round_controller import GameRoundController
from ui_components import (
    render_sidebar, render_bet_bar_chart, render_recommended_structures,
    render_final_structure, render_structure_table, render_player_detail_table, render_final_outcome_reason
)
from ui_actions import handle_new_round
from player_profiles import initialize_players, PlayerStats
from config import ROUND_TOTAL_DURATION

# 初始化 session 状态（含玩家、数据结构等）
initialize_session_state()
ensure_param_defaults()

if "sim_players" not in st.session_state:
    st.session_state.sim_players = initialize_players()
if "stat_players" not in st.session_state:
    st.session_state.stat_players = {pid: PlayerStats() for pid in st.session_state.sim_players.keys()}

# 下注玩家数量统计
betting_players = len([b for b in st.session_state.current_bets.values() if b])

# 渲染侧边栏 + 参数设置与控制按钮
simulate, import_next, uploaded_file, confidence, debug_speed = render_sidebar(
    round_id=st.session_state.round_id,
    online_count=st.session_state.online_base,
    betting_players=betting_players,
    countdown_bet=st.session_state.countdown_bet,
    countdown_result=st.session_state.countdown_result,
    time_to_next_round=st.session_state.time_to_next_round,
    debug_speed=st.session_state.debug_speed,
    std_bounds=st.session_state.structure_result_cache["std_bounds"] if st.session_state.structure_result_cache else None
)

if simulate:
    st.session_state.final_outcome = None
    st.session_state.structure_result_cache = None
    st.session_state.current_bets = {}
    handle_new_round()
    st.session_state._trigger_manual = True
    st.session_state._trigger_manual = True

# 页面主体布局
st.markdown("""
    <style>
    .block-container {
        max-width: 70vw !important;
        padding-right: 1rem;
        padding-left: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

left_col, right_col = st.columns([3, 4])
controller = GameRoundController(st.session_state)
visual = controller.get_visual_context() if st.session_state.structure_result_cache else {}

with left_col:
    total_bet_amt = sum(
        sum(bets.values()) for bets in st.session_state.current_bets.values()
    )
    if st.session_state.time_to_next_round < ROUND_TOTAL_DURATION and total_bet_amt > 0:
        render_bet_bar_chart(
            visual["structure_sums"],
            visual["highlight_areas"],
            visual["forced_areas"]
        )

    with st.container():
        if st.session_state.final_outcome:
            render_final_structure(
                st.session_state.final_outcome,
                st.session_state.forced_outcome is not None
            )
        elif st.session_state.structure_result_cache:
            recommended = [r["winning_areas"] for r in st.session_state.structure_result_cache["all_structures"] if r.get("within_confidence")]
            render_recommended_structures(recommended)

        if st.session_state.structure_result_cache:
            render_final_outcome_reason(
                st.session_state.final_outcome,
                st.session_state.structure_result_cache["all_structures"],
                st.session_state.structure_result_cache["std_bounds"]
            )

    structure_data = st.session_state.structure_result_cache or {}
    table_df = pd.DataFrame(structure_data.get("all_structures", []))
    if not table_df.empty:
        render_structure_table(
            table_df,
            st.session_state.current_bets,
            st.session_state.forced_outcome,
            st.session_state.time_to_next_round
        )

with right_col:
    if st.session_state.time_to_next_round < ROUND_TOTAL_DURATION:
        if st.session_state.current_bets:
            render_player_detail_table(
                st.session_state.current_bets,
                st.session_state.stat_players
            )

# ✅ 自动推进控制器
manual_triggered = st.session_state.pop("_trigger_manual", False)

# ✅ 1. 当前是运行中，继续推进
if st.session_state.running:
    if not manual_triggered:
        controller.tick()

    time.sleep(1.0 / st.session_state.debug_speed)

    from streamlit.runtime.scriptrunner import RerunException, RerunData
    raise RerunException(RerunData())

# ✅ 2. 如果运行结束，并且用户勾选了“自动”，则自动开启新一局
elif st.session_state.get("auto_simulate", False):
    handle_new_round()
    st.session_state._trigger_manual = True
    st.rerun()
