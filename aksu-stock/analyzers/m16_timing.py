"""
M16 — 现价交易择时评分（独立100分制）

5大评分维度：
  维度1 技术面择时状态    30分（趋势10+位置10+指标6+量能4）
  维度2 估值性价比        25分（历史分位10+行业对比8+回调幅度7）
  维度3 资金面承接力度    20分（近期流向8+筹码结构7+控盘状态5）
  维度4 情绪与催化适配    15分（板块情绪6+个股辨识5+催化窗口4）
  维度5 交易盈亏比风险    10分（盈亏比6+短期风险4）
"""
from __future__ import annotations
from datetime import datetime
from analyzers.base import ModuleResult, safe_float, pct_str, fmt_number


def analyze_timing(data: dict) -> ModuleResult:
    price = safe_float(data.get("price"))
    ma5 = safe_float(data.get("ma5"))
    ma10 = safe_float(data.get("ma10"))
    ma20 = safe_float(data.get("ma20"))
    ma60 = safe_float(data.get("ma60"))
    rsi14 = safe_float(data.get("rsi14"))
    dif = safe_float(data.get("dif"))
    dea = safe_float(data.get("dea"))
    kdj = data.get("kdj") or {}
    kdj_j = safe_float(kdj.get("j"))
    boll = data.get("boll") or {}
    boll_upper = safe_float(boll.get("upper"))
    boll_lower = safe_float(boll.get("lower"))
    turnover_rate = safe_float(data.get("turnover_rate"))
    pct_change = safe_float(data.get("pct_change"))
    pe_ttm = safe_float(data.get("pe_ttm"))
    week52_position = safe_float(data.get("week52_position"))
    main_net_inflow = safe_float(data.get("main_net_inflow"))
    main_net_ratio = safe_float(data.get("main_net_ratio"))
    holder_num_change_pct = safe_float(data.get("holder_num_change_pct"))
    dragon_tiger = data.get("dragon_tiger") or []
    market_sentiment = data.get("market_sentiment") or {}
    limit_up = safe_float(market_sentiment.get("limit_up_count"))
    limit_down = safe_float(market_sentiment.get("limit_down_count"))
    research_reports = data.get("research_reports") or []
    pledge_ratio = safe_float(data.get("pledge_ratio"))
    industry_peers = data.get("industry_peers") or []
    kline_df = data.get("kline_df")

    dim_detail: dict[str, float] = {}
    findings: list[str] = []

    # ═══════════════════════════════════════════
    # 维度1：技术面择时状态（满分30分）
    # ═══════════════════════════════════════════

    # 趋势方向（10分）
    d1_trend = 0.0
    if price and ma5 and ma10 and ma20 and ma60:
        bulls = sum([price > ma5, price > ma10, price > ma20, price > ma60])
        # 多周期共振加权
        d1_trend = bulls * 2.5  # 最高10分
        if ma5 and ma10 and ma20 and ma5 > ma10 > ma20:
            d1_trend = min(d1_trend + 1.0, 10.0)
            findings.append("趋势：均线多头排列，多周期共振向上")
        elif bulls == 0:
            d1_trend = max(d1_trend - 1.0, 0)
            findings.append("⚠️ 趋势：价格跌破全部均线，空头格局")
    elif price and ma20:
        d1_trend = 6.0 if price > ma20 else 3.0
    else:
        d1_trend = 5.0  # 数据缺失给中性分
    dim_detail["趋势方向"] = round(min(d1_trend, 10.0), 1)

    # 价格位置（10分）
    d1_position = 5.0
    if boll_lower and boll_upper and price:
        boll_width = boll_upper - boll_lower
        boll_pct = (price - boll_lower) / boll_width * 100 if boll_width > 0 else 50
        if boll_pct < 15:
            d1_position = 10.0
            findings.append(f"位置：价格触及布林下轨，技术超跌，反弹概率高")
        elif boll_pct < 30:
            d1_position = 8.0
            findings.append(f"位置：价格处于布林下方区间 ({boll_pct:.0f}%)，低位布局机会")
        elif boll_pct < 60:
            d1_position = 6.0
        elif boll_pct < 80:
            d1_position = 4.0
        else:
            d1_position = 1.0
            findings.append(f"⚠️ 位置：价格接近布林上轨，追高风险大")
    elif week52_position is not None:
        if week52_position < 20:
            d1_position = 9.0
        elif week52_position < 40:
            d1_position = 7.0
        elif week52_position < 70:
            d1_position = 5.0
        else:
            d1_position = 2.0
    dim_detail["价格位置"] = round(d1_position, 1)

    # 指标信号（6分）
    d1_indicator = 3.0
    indicator_notes: list[str] = []
    if rsi14 is not None:
        if rsi14 < 25:
            d1_indicator += 2.0
            indicator_notes.append(f"RSI {rsi14:.0f}（极度超卖）")
        elif rsi14 < 35:
            d1_indicator += 1.0
            indicator_notes.append(f"RSI {rsi14:.0f}（超卖）")
        elif rsi14 > 75:
            d1_indicator -= 2.0
            indicator_notes.append(f"RSI {rsi14:.0f}（超买）")
    if dif is not None and dea is not None:
        if dif > dea:
            d1_indicator += 1.0
            indicator_notes.append("MACD金叉")
        else:
            d1_indicator -= 1.0
            indicator_notes.append("MACD死叉")
    if kdj_j is not None:
        if kdj_j < 10:
            d1_indicator += 1.0
            indicator_notes.append(f"KDJ-J={kdj_j:.0f}（超卖）")
        elif kdj_j > 90:
            d1_indicator -= 1.0
            indicator_notes.append(f"KDJ-J={kdj_j:.0f}（超买）")
    if indicator_notes:
        findings.append("指标：" + "，".join(indicator_notes[:3]))
    dim_detail["指标信号"] = round(max(0.0, min(6.0, d1_indicator)), 1)

    # 量能配合（4分）
    d1_volume = 2.0
    if kline_df is not None and not kline_df.empty and "volume" in kline_df.columns:
        volumes = kline_df["volume"].tolist()
        if len(volumes) >= 5:
            avg_vol = sum(volumes[-5:]) / 5
            today_vol = data.get("volume")
            if today_vol and avg_vol > 0:
                vr = safe_float(today_vol) / avg_vol if safe_float(today_vol) else 1.0
                if vr and vr > 1.5 and pct_change and pct_change > 0:
                    d1_volume = 4.0
                    findings.append("量能：放量上涨，主动买盘强")
                elif vr and vr < 0.7 and pct_change and pct_change < 0:
                    d1_volume = 3.5
                    findings.append("量能：缩量回调，抛压有限")
                elif vr and vr > 1.5 and pct_change and pct_change < 0:
                    d1_volume = 1.0
                    findings.append("⚠️ 量能：放量下跌，出货迹象")
                else:
                    d1_volume = 2.5
    elif turnover_rate is not None:
        if 1 < turnover_rate < 5 and pct_change and pct_change > 0:
            d1_volume = 3.5
        elif turnover_rate > 8:
            d1_volume = 1.5
    dim_detail["量能配合"] = round(d1_volume, 1)

    dim1_total = dim_detail["趋势方向"] + dim_detail["价格位置"] + dim_detail["指标信号"] + dim_detail["量能配合"]
    dim1_total = min(30.0, max(0.0, dim1_total))

    # ═══════════════════════════════════════════
    # 维度2：估值性价比（满分25分）
    # ═══════════════════════════════════════════

    # 历史估值分位（10分）：用52周位置近似
    d2_hist_pe = 5.0
    if week52_position is not None:
        if week52_position < 20:
            d2_hist_pe = 10.0
        elif week52_position < 35:
            d2_hist_pe = 7.5
        elif week52_position < 60:
            d2_hist_pe = 5.0
        elif week52_position < 80:
            d2_hist_pe = 3.0
        else:
            d2_hist_pe = 1.0
    dim_detail["历史分位"] = round(d2_hist_pe, 1)

    # 行业估值对比（8分）
    d2_industry_pe = 4.0
    if pe_ttm and pe_ttm > 0 and industry_peers:
        peer_pes = [safe_float(p.get("pe_ttm")) for p in industry_peers
                    if safe_float(p.get("pe_ttm")) and safe_float(p.get("pe_ttm"), 0) > 0]
        if peer_pes:
            avg_pe = sum(peer_pes) / len(peer_pes)
            discount_pct = (avg_pe - pe_ttm) / avg_pe * 100
            if discount_pct > 30:
                d2_industry_pe = 8.0
                findings.append(f"估值：PE {pe_ttm:.1f}x，低于同业均值折价 {discount_pct:.0f}%，性价比极高")
            elif discount_pct > 15:
                d2_industry_pe = 6.5
            elif discount_pct > 0:
                d2_industry_pe = 5.0
            elif discount_pct > -15:
                d2_industry_pe = 3.5
            else:
                d2_industry_pe = 1.5
                findings.append(f"⚠️ 估值：PE溢价同业 {-discount_pct:.0f}%，当前不是好买点")
    elif pe_ttm:
        d2_industry_pe = 6.0 if pe_ttm < 20 else 4.0 if pe_ttm < 40 else 2.0
    dim_detail["行业对比"] = round(d2_industry_pe, 1)

    # 近期回调幅度（7分）
    d2_pullback = 3.5
    if kline_df is not None and not kline_df.empty and "close" in kline_df.columns:
        closes = kline_df["close"].tolist()
        if len(closes) >= 20 and price:
            recent_high = max(closes[-20:])
            pullback = (recent_high - price) / recent_high * 100 if recent_high > 0 else 0
            if pullback > 20:
                d2_pullback = 7.0
                findings.append(f"回调：近20日最高点已回调 {pullback:.1f}%，具备布局价值")
            elif pullback > 10:
                d2_pullback = 5.5
                findings.append(f"回调：近20日高点回调 {pullback:.1f}%，有一定回调深度")
            elif pullback > 5:
                d2_pullback = 4.0
            else:
                d2_pullback = 2.0
                findings.append("近期几乎无回调，追涨性价比低")
    dim_detail["回调幅度"] = round(d2_pullback, 1)

    dim2_total = dim_detail["历史分位"] + dim_detail["行业对比"] + dim_detail["回调幅度"]
    dim2_total = min(25.0, max(0.0, dim2_total))

    # ═══════════════════════════════════════════
    # 维度3：资金面承接力度（满分20分）
    # ═══════════════════════════════════════════

    # 近期资金流向（8分）
    d3_flow = 4.0
    if main_net_inflow is not None:
        if main_net_inflow > 5e7:
            d3_flow = 8.0
            findings.append(f"资金：主力大幅净流入 {main_net_inflow/1e8:.1f}亿，承接力度强")
        elif main_net_inflow > 1e7:
            d3_flow = 6.5
        elif main_net_inflow > 0:
            d3_flow = 5.0
        elif main_net_inflow > -1e7:
            d3_flow = 3.5
        elif main_net_inflow > -5e7:
            d3_flow = 2.0
            findings.append(f"⚠️ 资金：主力净流出 {abs(main_net_inflow)/1e8:.1f}亿，承接力度弱")
        else:
            d3_flow = 1.0
            findings.append(f"⚠️ 资金：主力大幅净流出，不建议现价买入")
    dim_detail["资金流向"] = round(d3_flow, 1)

    # 筹码结构稳定性（7分）
    d3_chip = 3.5
    if holder_num_change_pct is not None:
        if holder_num_change_pct < -10:
            d3_chip = 7.0
        elif holder_num_change_pct < -5:
            d3_chip = 5.5
        elif holder_num_change_pct < 0:
            d3_chip = 4.5
        elif holder_num_change_pct < 5:
            d3_chip = 3.5
        elif holder_num_change_pct < 10:
            d3_chip = 2.5
        else:
            d3_chip = 1.5
    dim_detail["筹码结构"] = round(d3_chip, 1)

    # 主力控盘状态（5分）
    d3_control = 2.5
    if dragon_tiger:
        net_vals = [safe_float(d.get("net")) for d in dragon_tiger if safe_float(d.get("net")) is not None]
        if net_vals and sum(net_vals) > 0:
            d3_control = 5.0
            findings.append("龙虎榜净买入，机构资金进场，控盘意图明确")
        elif net_vals and sum(net_vals) < 0:
            d3_control = 1.0
            findings.append("⚠️ 龙虎榜净卖出，警惕主力离场")
    elif main_net_ratio is not None:
        d3_control = 4.5 if main_net_ratio > 5 else 3.0 if main_net_ratio > 0 else 1.5
    dim_detail["控盘状态"] = round(d3_control, 1)

    dim3_total = dim_detail["资金流向"] + dim_detail["筹码结构"] + dim_detail["控盘状态"]
    dim3_total = min(20.0, max(0.0, dim3_total))

    # ═══════════════════════════════════════════
    # 维度4：情绪与催化适配度（满分15分）
    # ═══════════════════════════════════════════

    # 板块情绪周期（6分）
    d4_emotion = 3.0
    if limit_up is not None and limit_down is not None and limit_down >= 0:
        ratio = limit_up / max(limit_down + 1, 1)
        if ratio > 5:
            d4_emotion = 6.0
        elif ratio > 2:
            d4_emotion = 4.5
        elif ratio > 0.5:
            d4_emotion = 3.0
        else:
            d4_emotion = 1.0
            findings.append("⚠️ 情绪：全市场情绪悲观，不利于多头")
    dim_detail["板块情绪"] = round(d4_emotion, 1)

    # 个股辨识度（5分）
    d4_identify = 2.5
    if dragon_tiger:
        d4_identify = 5.0
    elif research_reports and len(research_reports) >= 5:
        d4_identify = 4.5
    elif research_reports and len(research_reports) >= 2:
        d4_identify = 3.5
    else:
        d4_identify = 2.5
    dim_detail["个股辨识度"] = round(d4_identify, 1)

    # 近期催化窗口（4分）
    month = datetime.now().month
    d4_catalyst = 2.0
    if month in [1, 2, 3, 4, 7, 8, 10]:
        d4_catalyst = 4.0  # 业绩窗口期
    elif len(research_reports) >= 3:
        d4_catalyst = 3.0
    dim_detail["催化窗口"] = round(d4_catalyst, 1)

    dim4_total = dim_detail["板块情绪"] + dim_detail["个股辨识度"] + dim_detail["催化窗口"]
    dim4_total = min(15.0, max(0.0, dim4_total))

    # ═══════════════════════════════════════════
    # 维度5：交易盈亏比与风险（满分10分）
    # ═══════════════════════════════════════════

    # 盈亏比（6分）
    d5_rr = 3.0
    stop = None
    target = None
    if price and ma20 and boll_lower:
        stop = min(ma20 * 0.97, boll_lower * 0.995)
    elif price and ma20:
        stop = ma20 * 0.97
    elif price:
        stop = price * 0.95

    if price and ma60:
        target = ma60 * 1.02 if price < ma60 else price * 1.12
    elif price:
        target = price * 1.10

    if price and stop and target and price > stop:
        risk = price - stop
        reward = target - price
        if risk > 0:
            rr = reward / risk
            if rr >= 3:
                d5_rr = 6.0
            elif rr >= 2:
                d5_rr = 4.5
            elif rr >= 1.5:
                d5_rr = 3.0
            elif rr >= 1:
                d5_rr = 2.0
            else:
                d5_rr = 1.0
                findings.append(f"⚠️ 盈亏比 {rr:.1f}:1，当前位置性价比差")
    dim_detail["盈亏比"] = round(d5_rr, 1)

    # 短期风险冲击（4分）
    d5_risk = 3.0
    if pledge_ratio and pledge_ratio > 40:
        d5_risk = 1.0
        findings.append(f"⚠️ 质押比例 {pct_str(pledge_ratio)}，爆仓风险影响近期走势")
    elif pct_change and pct_change < -5:
        d5_risk = 1.5
        findings.append("今日大跌，短期存在持续下跌压力")
    elif rsi14 and rsi14 > 75:
        d5_risk = 2.0
    else:
        d5_risk = 3.5 if not (pledge_ratio and pledge_ratio > 20) else 2.5
    dim_detail["短期风险"] = round(d5_risk, 1)

    dim5_total = dim_detail["盈亏比"] + dim_detail["短期风险"]
    dim5_total = min(10.0, max(0.0, dim5_total))

    # ═══════════════════════════════════════════
    # 汇总
    # ═══════════════════════════════════════════
    timing_score = round(dim1_total + dim2_total + dim3_total + dim4_total + dim5_total, 1)
    timing_score = max(0.0, min(100.0, timing_score))

    # 择时等级
    if timing_score >= 90:
        timing_level = "极佳买入时点"
        timing_color = "deep-green"
    elif timing_score >= 80:
        timing_level = "良好买入时点"
        timing_color = "light-green"
    elif timing_score >= 70:
        timing_level = "中性试错时点"
        timing_color = "yellow"
    elif timing_score >= 60:
        timing_level = "偏弱观望时点"
        timing_color = "orange"
    else:
        timing_level = "极差回避时点"
        timing_color = "red"

    # 操作结论
    if timing_score >= 80:
        operation = "✅ 现价可积极买入，建议分批进场（首仓30%-50%）"
    elif timing_score >= 70:
        operation = "⚡ 可轻仓试多，等待信号确认后加仓（首仓20%-30%）"
    elif timing_score >= 60:
        operation = "⏸️ 建议观望，等待更好买入时机（回调5%-10%再考虑）"
    else:
        operation = "🚫 不建议现价买入，风险大于机会，等待技术底部确认"

    return ModuleResult(
        module_id="M16",
        module_name="现价交易择时评分",
        score=timing_score / 10,  # 转换为10分制供M17使用
        stars=max(1, min(5, int(timing_score / 20))),
        key_findings=findings[:6],
        short_advice=operation,
        mid_advice=f"中线：维度2估值得分 {dim2_total:.1f}/25，{'估值处于低位，可中线布局' if dim2_total >= 17 else '估值偏高，控制中线仓位'}",
        long_advice=f"长线：维度1技术得分 {dim1_total:.1f}/30，{'多头趋势确立，可配置长线仓位' if dim1_total >= 20 else '技术趋势偏弱，长线需等待趋势逆转'}",
        conclusion=f"【现价择时评分】{timing_score:.1f}/100 — {timing_level}",
        detail={
            "timing_score": timing_score,
            "timing_level": timing_level,
            "timing_color": timing_color,
            "operation": operation,
            "dim1_technical": round(dim1_total, 1),
            "dim2_valuation": round(dim2_total, 1),
            "dim3_capital": round(dim3_total, 1),
            "dim4_sentiment": round(dim4_total, 1),
            "dim5_riskReward": round(dim5_total, 1),
            "dim_detail": dim_detail,
            "stop_loss": round(stop, 2) if stop else None,
            "target": round(target, 2) if target else None,
        },
    )
