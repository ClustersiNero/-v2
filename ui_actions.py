import streamlit as st
from config import ROUND_TOTAL_DURATION, BETTING_DURATION, WAITING_DURATION

def handle_new_round():
    """
    处理点击“开始新局”按钮，重置状态，重新初始化下注计划等。
    """
    if st.session_state.has_started:
        st.session_state.round_id += 1
    else:
        st.session_state.has_started = True  # 首次点击不 +1，标记为已开始
    st.session_state.time_to_next_round = ROUND_TOTAL_DURATION
    st.session_state.countdown_bet = BETTING_DURATION
    st.session_state.countdown_result = WAITING_DURATION
    st.session_state.current_bets = {}
    st.session_state.final_outcome = None
    st.session_state.forced_outcome = None
    st.session_state.structure_result_cache = None
    st.session_state.running = True

    # ✅ 将当前控件参数快照记录为当前局所用值
    st.session_state._active_rtp = st.session_state.target_rtp
    st.session_state._active_confidence = st.session_state.confidence_level

def handle_imported_round(imported_bets):
    """
    处理点击“导入下一局”按钮，加载外部下注数据，重置状态。
    """
    st.session_state.round_id += 1
    st.session_state.time_to_next_round = ROUND_TOTAL_DURATION
    st.session_state.countdown_bet = BETTING_DURATION
    st.session_state.countdown_result = WAITING_DURATION
    st.session_state.current_bets = imported_bets
    st.session_state.final_outcome = None
    st.session_state.forced_outcome = None
    st.session_state.structure_result_cache = None
    st.session_state.running = True

    # ✅ 同样记录参数快照
    st.session_state._active_rtp = st.session_state.target_rtp
    st.session_state._active_confidence = st.session_state.confidence_level
