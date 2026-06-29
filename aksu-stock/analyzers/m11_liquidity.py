"""M11 — 量能换手与流动性专项分析（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_liquidity(data: dict) -> ModuleResult:
    turnover_rate = safe_float(data.get("turnover_rate"))
    volume = safe_float(data.get("volume"))
    amount = safe_float(data.get("amount"))
    pct_change = safe_float(data.get("pct_change"))
    market_cap = safe_float(data.get("market_cap"))
    kline_df = data.get("kline_df")

    findings: list[str] = []

    # ── 流动性安全性（3分）──
    score_safety = 1.5
    if amount is not None:
        amt_yi = amount / 1e8
        if amt_yi > 10:
            score_safety = 3.0
            findings.append(f"今日成交额 {fmt_number(amt_yi, 2)} 亿，流动性充裕，无流动性枯竭风险")
        elif amt_yi > 2:
            score_safety = 2.5
            findings.append(f"今日成交额 {fmt_number(amt_yi, 2)} 亿，流动性良好")
        elif amt_yi > 0.5:
            score_safety = 2.0
            findings.append(f"今日成交额 {fmt_number(amt_yi, 2)} 亿，流动性一般")
        else:
            score_safety = 1.0
            findings.append(f"⚠️ 今日成交额 {fmt_number(amt_yi, 2)} 亿，流动性偏低，大资金进出摩擦成本高")
    elif market_cap is not None:
        if market_cap < 2e9:  # 20亿以下
            findings.append("⚠️ 市值极小，需关注流动性枯竭风险和闪崩风险")
            score_safety = 1.0

    # ── 量能结构健康度（4分）──
    score_volume_health = 2.0
    # 计算近20日均量
    if kline_df is not None and not kline_df.empty:
        volumes = kline_df["volume"].tolist() if "volume" in kline_df.columns else []
        if len(volumes) >= 20 and volume is not None:
            avg_volume_20 = sum(volumes[-20:]) / 20
            volume_ratio = volume / avg_volume_20 if avg_volume_20 > 0 else 1.0
            findings.append(f"今日量比 {fmt_number(volume_ratio, 2)}（今日量/近20日均量）")
            # 结合涨跌分析量价关系
            if volume_ratio > 2 and pct_change and pct_change > 2:
                score_volume_health = 4.0
                findings.append("放量上涨，量价齐升，主动买盘强烈，量能结构健康")
            elif volume_ratio > 2 and pct_change and pct_change < -2:
                score_volume_health = 1.0
                findings.append("⚠️ 放量下跌，出货信号，量能结构恶化")
            elif volume_ratio < 0.5 and pct_change and pct_change > 0:
                score_volume_health = 2.5
                findings.append("缩量上涨，筹码锁仓，量能健康（缩量涨是洗盘后续拉升前兆）")
            elif volume_ratio < 0.5 and pct_change and pct_change < 0:
                score_volume_health = 2.5
                findings.append("缩量回调，主动卖压不大，正常获利了结")
            elif 0.7 < volume_ratio < 1.5:
                score_volume_health = 2.5
                findings.append("量能平稳，成交正常，无异常信号")
            else:
                score_volume_health = 2.0
        elif volumes and len(volumes) >= 5 and volume is not None:
            avg_5 = sum(volumes[-5:]) / 5
            vr = volume / avg_5 if avg_5 > 0 else 1.0
            findings.append(f"量比约 {vr:.2f}（基于近5日均量估算）")

    # ── 换手合理性（3分）──
    score_turnover = 1.5
    if turnover_rate is not None:
        if 1 < turnover_rate <= 3:
            score_turnover = 3.0
            findings.append(f"换手率 {pct_str(turnover_rate)}（健康区间1%-3%），筹码交换效率理想")
        elif 3 < turnover_rate <= 8:
            score_turnover = 2.5
            findings.append(f"换手率 {pct_str(turnover_rate)}（中高区间），活跃度高，短线机会多")
        elif turnover_rate > 8:
            score_turnover = 1.5
            findings.append(f"换手率 {pct_str(turnover_rate)}（过高，>8%），博弈激烈，短线风险大")
        elif turnover_rate < 0.3:
            score_turnover = 1.0
            findings.append(f"⚠️ 换手率极低（{pct_str(turnover_rate)}），成交极度清淡，有流动性枯竭风险")
        else:
            score_turnover = 1.5
            findings.append(f"换手率 {pct_str(turnover_rate)}，成交偏低")

    total = score_safety + score_volume_health + score_turnover
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M11",
        module_name="量能换手与流动性专项",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice=f"短线：换手率 {pct_str(turnover_rate)}，{'高换手适合做T' if turnover_rate and turnover_rate > 5 else '低换手控制仓位，等待放量'}",
        mid_advice="中线：关注每周成交额变化，缩量整理后的放量突破是中线加仓信号",
        long_advice="长线：日均成交额>1亿是基本流动性门槛，低于此标准不建议大额建仓",
        conclusion=f"量能流动性评分 {total:.1f}/10，今日成交额 {fmt_number((amount or 0)/1e8, 2)} 亿，换手率 {pct_str(turnover_rate)}",
        detail={
            "amount": amount, "turnover_rate": turnover_rate,
            "volume": volume, "pct_change": pct_change,
        },
    )
