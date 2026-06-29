"""M06 — 多周期技术面实时操盘分析（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, fmt_number, pct_str


def analyze_technical(data: dict) -> ModuleResult:
    price = safe_float(data.get("price"))
    ma5 = safe_float(data.get("ma5"))
    ma10 = safe_float(data.get("ma10"))
    ma20 = safe_float(data.get("ma20"))
    ma60 = safe_float(data.get("ma60"))
    ma120 = safe_float(data.get("ma120"))
    rsi14 = safe_float(data.get("rsi14"))
    dif = safe_float(data.get("dif"))
    dea = safe_float(data.get("dea"))
    macd_bar = safe_float(data.get("macd"))
    kdj = data.get("kdj") or {}
    boll = data.get("boll") or {}
    kdj_k = safe_float(kdj.get("k"))
    kdj_d = safe_float(kdj.get("d"))
    kdj_j = safe_float(kdj.get("j"))
    boll_upper = safe_float(boll.get("upper"))
    boll_mid = safe_float(boll.get("mid"))
    boll_lower = safe_float(boll.get("lower"))
    pct_change = safe_float(data.get("pct_change"))
    turnover_rate = safe_float(data.get("turnover_rate"))
    kline_df = data.get("kline_df")

    findings: list[str] = []

    # ── 趋势一致性（3分）──
    score_trend = 1.5
    trend_signals: list[str] = []
    if price and ma5 and ma10 and ma20 and ma60:
        bulls = sum([price > ma5, price > ma10, price > ma20, price > ma60])
        if bulls == 4:
            score_trend = 3.0
            trend_signals.append("多周期多头共振（价格>MA5/10/20/60），趋势强势")
        elif bulls >= 3:
            score_trend = 2.5
            trend_signals.append(f"价格站上 {bulls}/4 均线，趋势偏多")
        elif bulls >= 2:
            score_trend = 2.0
            trend_signals.append(f"价格站上 {bulls}/4 均线，多空争夺")
        elif bulls == 1:
            score_trend = 1.0
            trend_signals.append("价格仅站上1条均线，空头趋势主导")
        else:
            score_trend = 0.5
            trend_signals.append("⚠️ 价格跌破全部主要均线，空头格局明确")

        # 均线多头排列检查
        if ma5 and ma10 and ma20 and ma5 > ma10 > ma20:
            trend_signals.append("短期均线多头排列（MA5>MA10>MA20）")
            score_trend = min(score_trend + 0.3, 3.0)
        elif ma5 and ma10 and ma20 and ma5 < ma10 < ma20:
            trend_signals.append("⚠️ 短期均线空头排列（MA5<MA10<MA20）")
            score_trend = max(score_trend - 0.3, 0.5)
    else:
        trend_signals.append("均线数据部分缺失，趋势判断有限")

    if ma120:
        findings.append(f"MA120：{fmt_number(ma120, 2)}（{'价格站上年线，长期趋势向好' if price and price > ma120 else '⚠️ 价格跌破年线，长期趋势偏弱'}）")
    findings.extend(trend_signals[:2])

    # ── 量价配合度（3分）──
    score_volume = 1.5
    if turnover_rate is not None:
        if 1 < turnover_rate < 5:
            score_volume = 2.5
            findings.append(f"换手率 {pct_str(turnover_rate)}，量能适中，量价配合健康")
        elif turnover_rate >= 5:
            if pct_change and pct_change > 0:
                score_volume = 3.0
                findings.append(f"换手率 {pct_str(turnover_rate)}，成交放量上涨，主动性买盘强")
            else:
                score_volume = 1.0
                findings.append(f"⚠️ 换手率 {pct_str(turnover_rate)}，放量下跌，出货信号")
        elif turnover_rate <= 1:
            score_volume = 1.5
            findings.append(f"换手率 {pct_str(turnover_rate)}，成交清淡，关注缩量反弹机会")

    # ── 形态有效性（2分）──
    score_pattern = 1.5
    if boll_mid and boll_upper and boll_lower and price:
        boll_width = boll_upper - boll_lower
        boll_pos = (price - boll_lower) / boll_width if boll_width > 0 else 0.5
        if boll_pos < 0.2:
            score_pattern = 2.0
            findings.append(f"价格触及布林下轨（BOLL下 {fmt_number(boll_lower, 2)}），超跌反弹机会")
        elif boll_pos > 0.85:
            score_pattern = 1.0
            findings.append(f"⚠️ 价格接近布林上轨（BOLL上 {fmt_number(boll_upper, 2)}），注意短期获利了结")
        else:
            score_pattern = 1.5
            findings.append(f"BOLL中轨 {fmt_number(boll_mid, 2)}，价格处于布林通道 {boll_pos*100:.0f}% 位置")

    # ── 指标共振度（2分）──
    score_indicator = 1.5
    indicator_signals: list[str] = []
    # RSI
    if rsi14 is not None:
        if rsi14 < 30:
            score_indicator = min(score_indicator + 0.5, 2.0)
            indicator_signals.append(f"RSI {fmt_number(rsi14, 1)}（超卖区，反弹概率高）")
        elif rsi14 > 70:
            score_indicator = max(score_indicator - 0.5, 0.5)
            indicator_signals.append(f"RSI {fmt_number(rsi14, 1)}（⚠️ 超买区，短期调整风险）")
        else:
            indicator_signals.append(f"RSI {fmt_number(rsi14, 1)}（中性）")
    # MACD
    if dif is not None and dea is not None:
        if dif > dea and dif > 0:
            score_indicator = min(score_indicator + 0.3, 2.0)
            indicator_signals.append(f"MACD金叉且在零轴上方（DIF {fmt_number(dif, 3)} > DEA {fmt_number(dea, 3)}），多头动能强")
        elif dif > dea and dif < 0:
            indicator_signals.append(f"MACD零轴下方金叉（DIF {fmt_number(dif, 3)}），底部反弹信号")
            score_indicator = min(score_indicator + 0.2, 2.0)
        elif dif < dea:
            score_indicator = max(score_indicator - 0.3, 0.5)
            indicator_signals.append(f"⚠️ MACD死叉（DIF {fmt_number(dif, 3)} < DEA {fmt_number(dea, 3)}），空头压力")
    # KDJ
    if kdj_j is not None:
        if kdj_j < 10:
            indicator_signals.append(f"KDJ-J {fmt_number(kdj_j, 1)}（超卖，底部信号）")
            score_indicator = min(score_indicator + 0.2, 2.0)
        elif kdj_j > 90:
            indicator_signals.append(f"KDJ-J {fmt_number(kdj_j, 1)}（⚠️ 超买，注意调整）")
            score_indicator = max(score_indicator - 0.2, 0.5)
    findings.extend(indicator_signals[:3])

    total = score_trend + score_volume + score_pattern + score_indicator
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    # 关键位计算
    support = ma20 or ma10 or boll_mid
    resistance = boll_upper or (ma60 if ma60 and price and price < ma60 else None)
    stop_loss = boll_lower or (ma20 and ma20 * 0.97 if ma20 else None)

    return ModuleResult(
        module_id="M06",
        module_name="多周期技术面实时操盘",
        score=total,
        stars=stars,
        key_findings=findings[:6],
        short_advice=f"短线入场区：{fmt_number(support, 2)} 附近，止损：{fmt_number(stop_loss, 2)}，止盈关注：{fmt_number(resistance, 2)}",
        mid_advice=f"中线：MA60 {fmt_number(ma60, 2)} 为中线多空分界，{'站稳可中线持有' if price and ma60 and price > ma60 else '跌破需谨慎'}",
        long_advice=f"长线：MA120 {fmt_number(ma120, 2)} 为年线支撑，{'站稳年线是长线多头前提' if price and ma120 and price > ma120 else '跌破年线规避长线布局'}",
        conclusion=f"技术面评分 {total:.1f}/10，{'多头趋势' if score_trend >= 2.5 else '震荡格局' if score_trend >= 1.8 else '空头格局'}，RSI {fmt_number(rsi14, 1)}，MACD {'金叉' if dif and dea and dif > dea else '死叉' if dif and dea else '—'}",
        detail={
            "price": price, "ma5": ma5, "ma10": ma10, "ma20": ma20,
            "ma60": ma60, "ma120": ma120, "rsi14": rsi14,
            "dif": dif, "dea": dea, "macd_bar": macd_bar,
            "kdj": kdj, "boll": boll,
            "support": support, "resistance": resistance, "stop_loss": stop_loss,
        },
    )
