import streamlit as st
import pandas as pd
import altair as alt
from config import PAYOUT_RATES, ROUND_TOTAL_DURATION, BETTING_DURATION, WAITING_DURATION, ANIMATION_DURATION


# ✅ 渲染侧边栏（包含基础信息 + 策略参数 + 倒计时 + 模拟/导入按钮）
def render_sidebar(round_id, online_count, betting_players, countdown_bet, countdown_result, time_to_next_round, debug_speed=1.0, ci_text=None, std_bounds=None):
    st.sidebar.markdown("<h4>📋 对局基础信息</h4>", unsafe_allow_html=True)
    st.sidebar.text(f"游戏名：摩天轮")
    st.sidebar.text(f"对局数ID：{round_id}")
    st.sidebar.text(f"在线人数：{online_count}")
    st.sidebar.text(f"参与人数：{betting_players}")

    st.sidebar.markdown("<h4>🎯 策略参数配置</h4>", unsafe_allow_html=True)
    if "platform_pool" in st.session_state:
        pool = st.session_state.platform_pool
        st.sidebar.text(f"当前水池值：{int(pool.get_pool_value()):,}")
        st.sidebar.text(f"当前目标RTP：{pool.get_current_rtp_target() * 100:.1f}%")

    confidence = st.sidebar.slider("📐 置信度", min_value=0.80, max_value=0.999, step=0.001, format="%.3f", value=0.95, key="confidence_level")
    if std_bounds:
        low, high = std_bounds
        st.sidebar.text(f"置信区间：{low:.3f} ~ {high:.3f}")

    st.sidebar.markdown("<h4>⏱ 当前阶段与强控窗口</h4>", unsafe_allow_html=True)
    phase_progress_info(time_to_next_round, countdown_bet, countdown_result)

    st.sidebar.markdown("<hr>", unsafe_allow_html=True)
    debug_speed = st.sidebar.slider("⏩ 模拟倍速", min_value=0.1, max_value=5.0, step=0.1, key="debug_speed")

    col1, col2 = st.sidebar.columns([5, 1])
    with col1:
        simulate = st.button("🚀 模拟下一局下注")
    with col2:
        auto_simulate = st.checkbox("自动", key="auto_simulate", value=st.session_state.get("auto_simulate", False))    

    uploaded_file = st.sidebar.file_uploader("📥 导入Excel下注文件", type=["xls", "xlsx"])
    import_next = st.sidebar.button("📄 读取下一局下注数据")

    return simulate, import_next, uploaded_file, confidence, debug_speed


def phase_progress_info(time_to_next_round, countdown_bet, countdown_result):
    """
    统一处理当前阶段与进度展示逻辑，避免 render_sidebar 过长。
    """
    if time_to_next_round > (ROUND_TOTAL_DURATION - BETTING_DURATION):
        st.sidebar.markdown("**下注阶段**")
        progress_ratio_bet = max(0.0, min(1.0, countdown_bet / BETTING_DURATION))
        progress_ratio_window = max(0.0, min(1.0, (countdown_bet + countdown_result) / (ROUND_TOTAL_DURATION - ANIMATION_DURATION)))
        st.sidebar.progress(progress_ratio_bet, text=f"剩余下注时间：{max(0, int(countdown_bet))}s")
        st.sidebar.progress(progress_ratio_window, text=f"✅ 强控窗口剩余：{max(0, int(countdown_bet + countdown_result))}s")
    elif time_to_next_round > ANIMATION_DURATION:
        st.sidebar.markdown("**等待开奖阶段**")
        progress_ratio_result = max(0.0, min(1.0, countdown_result / WAITING_DURATION))
        progress_ratio_window = max(0.0, min(1.0, countdown_result / (ROUND_TOTAL_DURATION - ANIMATION_DURATION)))
        st.sidebar.progress(progress_ratio_result, text=f"剩余等待时间：{max(0, int(countdown_result))}s")
        st.sidebar.progress(progress_ratio_window, text=f"✅ 强控窗口剩余：{max(0, int(countdown_result))}s")
    else:
        st.sidebar.markdown("**开奖动画阶段**")
        value = max(0.0, min(1.0, time_to_next_round / ANIMATION_DURATION))
        st.sidebar.progress(value, text=f"开奖动画时间：{time_to_next_round}s")
        st.sidebar.text("❌ 当前不可强制开奖")

# ✅ 渲染下注柱状图 + 推荐高亮 + 强控标记
def render_bet_bar_chart(structure_sums, highlight_areas, forced_areas=None):
    st.markdown("<h4 style='margin-top: 0.8rem; margin-bottom: 0.2rem'>📊 投注分布概览</h4>", unsafe_allow_html=True)
    df = pd.DataFrame.from_dict(structure_sums, orient="index", columns=["下注总额"])
    df.index.name = "区域"
    df = df.reset_index()
    forced_set = set(forced_areas) if forced_areas is not None else set()
    df["颜色"] = df["区域"].apply(
        lambda x: "强控" if x in forced_set else (
            "推荐" if x in highlight_areas else "默认")
    )
    color_map = {"强控": "crimson", "推荐": "green", "默认": "steelblue"}
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("区域:N", axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y("下注总额:Q"),
        color=alt.Color("颜色:N", scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())), legend=None)
    ).properties(height=240)
    st.altair_chart(chart, use_container_width=True)

# ✅ 渲染推荐结构文本
def render_recommended_structures(recommended: list[list[int]]):
    """
    渲染推荐结构展示区域，支持无推荐时输出占位信息。
    """
    if not recommended:
        st.markdown("<h4>推荐结构：[ ]</h4>", unsafe_allow_html=True)
        return

    all_text = "，".join(
        f"[ {', '.join(map(str, r))} ]" for r in recommended
    )
    st.markdown(f"<h4>推荐结构：{all_text}</h4>", unsafe_allow_html=True)

# ✅ 渲染开奖结构文本
def render_final_structure(outcome, forced_flag):
    prefix = "【强控】" if forced_flag else ""
    st.markdown(
        f"<h4 style='margin-top: -0.5rem; font-weight: 600'>{prefix}开奖结果：{outcome['winning_areas']} (STD: {outcome['std']:.4f})</h4>",
        unsafe_allow_html=True
    )


# ✅ 渲染控奖结构模拟结果表格（高亮推荐 + 红框强控）
def render_structure_table(table_df, current_bets, forced_outcome, time_to_next_round):
    if table_df.empty:
        return

    st.markdown("<h4 style='margin-top: 0.8rem; margin-bottom: 0.2rem'>🎯 控奖结构模拟结果</h4>", unsafe_allow_html=True)
    headers = ["区域", "累计投注", "预计开奖", "系统盈亏", "RTP_STD", "符合预期", "态势STD", "强制开奖"]
    header_cols = st.columns(len(headers), gap="small")
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"**{h}**")

    forced_key = forced_outcome["winning_areas"] if isinstance(forced_outcome, dict) and "winning_areas" in forced_outcome else None

    for i, row in table_df.iterrows():
        is_forced = forced_key is not None and row["winning_areas"] == forced_key
        cols = st.columns(len(headers), gap="small")
        win_areas = ",".join(map(str, row["winning_areas"]))
        est_award = 0
        related_bet = 0
        total_bet = sum(sum(bets.values()) for bets in current_bets.values())
        for bets in current_bets.values():
            for a, v in bets.items():
                if a in row["winning_areas"]:
                    related_bet += v
                    est_award += v * PAYOUT_RATES[a]
        profit = total_bet - est_award
        std = row["std"]
        memory_effect = row.get("memory_effect", 0.0)
        within = row["within_confidence"]

        highlight_style = "background-color: rgba(255,0,0,0.1); border-left: 4px solid red; padding: 6px; border-radius: 5px;" if is_forced else ""
        cols[0].markdown(f"<div style='{highlight_style}'>{win_areas}</div>", unsafe_allow_html=True)
        cols[1].markdown(f"<div style='{highlight_style}'>{related_bet:,.0f}</div>", unsafe_allow_html=True)
        cols[2].markdown(f"<div style='{highlight_style}'>{est_award:,.0f}</div>", unsafe_allow_html=True)
        cols[3].markdown(f"<div style='{highlight_style}'>{profit:,.0f}</div>", unsafe_allow_html=True)
        cols[4].markdown(f"<div style='{highlight_style}'>{std:.2f}</div>", unsafe_allow_html=True)
        cols[6].markdown(f"<div style='{highlight_style}'>{'√' if within else '×'}</div>", unsafe_allow_html=True)
        cols[5].markdown(f"<div style='{highlight_style}'>{memory_effect:.2f}</div>", unsafe_allow_html=True)
        if time_to_next_round > ANIMATION_DURATION:
            force_btn_label = "🔴 取消" if is_forced else "确认"
            if cols[7].button(force_btn_label, key=f"force_btn_{i}"):
                st.session_state.forced_outcome = row.to_dict() if not is_forced else None
                st.rerun()
        else:
            cols[7].write("❌")

# ✅ 渲染玩家下注明细表格
def render_player_detail_table(current_bets, stat_players):
    st.markdown("<h4>👤 玩家下注明细</h4>", unsafe_allow_html=True)
    records = []
    index = 1
    for pid in sorted(current_bets.keys()):
        bets = current_bets[pid]
        total = sum(bets.values())
        stats = stat_players[pid]
        latest_rtp = getattr(stats, 'rtp', lambda: 0)()  # 避免异常，默认0
        row = {
            "序号": index,
            "UID": pid.replace('player_', ''),
            "总投注": total,
            "当前RTP": f"{latest_rtp * 100:.1f}%",
            "充值额度": st.session_state.sim_players[pid].recharge_amount
        }
        for a in range(1, 9):
            row[f"结构{a}"] = bets.get(a, 0)
        row["结构9"] = sum(bets.get(a, 0) for a in range(1, 5))
        row["结构10"] = sum(bets.get(a, 0) for a in range(5, 9))
        records.append(row)
        index += 1

    df = pd.DataFrame(records)
    numeric_cols = df.select_dtypes(include=['number']).columns
    df[numeric_cols] = df[numeric_cols].round(0).astype(int)

    profit_colors, loss_colors, yellow_colors = [], [], []

    for row in df.itertuples():
        bets = {f"结构{i}": getattr(row, f"结构{i}") for i in range(1, 11)}
        total = getattr(row, "总投注")

        profit_map = {}
        for i in range(1, 11):
            hit_areas = (
                [i] if i <= 8 else
                list(range(1, 5)) if i == 9 else
                list(range(5, 9))
            )
            payout = sum(bets.get(f"结构{a}", 0) * PAYOUT_RATES.get(a, 0) for a in hit_areas)
            profit_map[f"结构{i}"] = payout - total

        max_profit = max(profit_map.values())
        min_profit = min(profit_map.values())

        rtp_map = {}
        for i in range(1, 11):
            hit_areas = (
                [i] if i <= 8 else
                list(range(1, 5)) if i == 9 else
                list(range(5, 9))
            )
            payout = sum(bets.get(f"结构{a}", 0) * PAYOUT_RATES.get(a, 0) for a in hit_areas)
            rtp = payout / total if total > 0 else 0
            rtp_map[f"结构{i}"] = abs(rtp - 1)

        min_rtp_diff = min(rtp_map.values())

        colors_profit = ["" for _ in df.columns]
        colors_loss = ["" for _ in df.columns]
        colors_yellow = ["" for _ in df.columns]

        for i in range(1, 11):
            if profit_map[f"结构{i}"] == max_profit:
                colors_profit[df.columns.get_loc(f"结构{i}")] = "background-color: #d4edda"
            if profit_map[f"结构{i}"] == min_profit:
                colors_loss[df.columns.get_loc(f"结构{i}")] = "background-color: #f8d7da"
            if abs(rtp_map[f"结构{i}"] - min_rtp_diff) < 1e-8:
                colors_yellow[df.columns.get_loc(f"结构{i}")] = "background-color: #fff3cd"

        profit_colors.append(colors_profit)
        loss_colors.append(colors_loss)
        yellow_colors.append(colors_yellow)

    styled_df = df.style.format({col: "{:,.0f}" for col in numeric_cols})
    styled_df = styled_df.apply(lambda _: profit_colors.pop(0), axis=1)
    styled_df = styled_df.apply(lambda _: loss_colors.pop(0), axis=1)
    styled_df = styled_df.apply(lambda _: yellow_colors.pop(0), axis=1)
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=930)

def render_final_outcome_reason(outcome: dict, all_structures: list[dict], std_bounds: tuple[float, float]):
    """
    展示当前最终开奖结果结构被选中的原因。
    """
    # ✅ 尚未开奖，直接展示占位信息
    if not outcome or "winning_areas" not in outcome:
        st.markdown("<h4>当前结构：[ ]（尚未开奖）</h4>", unsafe_allow_html=True)
        return

    low, high = std_bounds
    std = outcome.get("std", 0)
    within = outcome.get("within_confidence", False)
    winning_areas = outcome.get("winning_areas", [])

    matching = [s for s in all_structures if s.get("within_confidence")]
    count_matching = len(matching)

    # ✅ 使用 st.container 保证区域结构一致
    with st.container():
        st.markdown("<h4>当前结构分析</h4>", unsafe_allow_html=True)
        if within:
            st.markdown(f"""
            ✅ 当前结构 `[ {', '.join(map(str, winning_areas))} ]` 的STD为 **{std:.4f}**，落在置信区间范围内（{low:.3f} ~ {high:.3f}）。

            - 当前匹配结构总数：{count_matching} 个、从中选择态势STD最小的结构
            """)
        else:
            st.markdown(f"""
            ❌ 当前结构 `[ {', '.join(map(str, winning_areas))} ]` 的STD为 **{std:.4f}**，未落在置信区间（{low:.3f} ~ {high:.3f}）。

            - 当前无结构命中置信区间、选择与目标 STD 最近的结构，且 限制平台赔付额 <= 200%投注额
            """)

        # ✅ 强制增加占位高度，避免 UI 抖动
        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)