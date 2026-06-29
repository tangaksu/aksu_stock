"""M16 多维加权综合投资策略总结"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt


# 加权权重配置（对应规格文档）
WEIGHTS = {
    # 基本面 30%（M01+M02+M03各占10%）
    "M01": 0.10,
    "M02": 0.10,
    "M03": 0.10,
    # 行业与估值 25%（M04+M05各占12.5%）
    "M04": 0.125,
    "M05": 0.125,
    # 市场博弈 25%（M06+M07+M08+M09各占6.25%）
    "M06": 0.0625,
    "M07": 0.0625,
    "M08": 0.0625,
    "M09": 0.0625,
    # 风控与催化 20%（M10+M11+M12+M13+M14各占4%）
    "M10": 0.04,
    "M11": 0.04,
    "M12": 0.04,
    "M13": 0.04,
    "M14": 0.04,
}

# 当实际覆盖权重比例超过此阈值时，按实际比例归一化折算总分
MIN_WEIGHT_COVERAGE = 0.95


def calc_weighted_score(module_results: dict) -> float:
    """计算100分制加权综合评分"""
    total = 0.0
    weight_used = 0.0
    for mid, weight in WEIGHTS.items():
        result = module_results.get(mid)
        if result and hasattr(result, "score"):
            total += result.score * weight * 10  # 10分制 → 100分制
            weight_used += weight
    # 若部分数据缺失，当已覆盖权重 < MIN_WEIGHT_COVERAGE 时按实际权重比例归一化折算
    if weight_used < MIN_WEIGHT_COVERAGE and weight_used > 0:
        total = total / weight_used
    return round(min(100.0, max(0.0, total)), 1)


def _rating_info(score: float) -> tuple[int, str, str]:
    """返回(星级, 等级名称, 颜色)"""
    if score >= 90:
        return 5, "极具投资价值", "#15803d"
    if score >= 80:
        return 4, "优质标的", "#16a34a"
    if score >= 70:
        return 3, "中性震荡", "#ca8a04"
    if score >= 60:
        return 2, "偏弱谨慎", "#ea580c"
    return 1, "规避离场", "#dc2626"


def _risk_level(score: float) -> str:
    if score >= 80:
        return "低风险"
    if score >= 70:
        return "中低风险"
    if score >= 60:
        return "中等风险"
    if score >= 50:
        return "中高风险"
    return "高风险"


def analyze_summary(data: dict, module_results: dict) -> ModuleResult:
    rt = data.get("realtime") or {}
    info = data.get("stock_info") or {}
    df = data.get("kline_df")

    code = data.get("code", "")
    name = rt.get("name") or info.get("name", code)
    price = rt.get("price")
    pct = rt.get("pct_change") or 0

    # ── 综合评分计算 ──
    total_score = calc_weighted_score(module_results)
    stars, rating_name, color = _rating_info(total_score)
    risk_level = _risk_level(total_score)

    findings = []
    findings.append(f"🏆 综合投资评分：{total_score:.1f}/100（{stars}星·{rating_name}）")
    findings.append(f"⚠️ 风险等级：{risk_level}")

    # ── 关键价位汇总 ──
    ma10 = ma20 = None
    if df is not None and not df.empty:
        close_col = "收盘" if "收盘" in df.columns else "close"
        closes = df[close_col].tolist()
        if len(closes) >= 20:
            ma10 = round(sum(closes[-10:]) / 10, 2)
            ma20 = round(sum(closes[-20:]) / 20, 2)

    if price:
        entry_low = round(price * 0.98, 2)
        entry_high = round(price * 1.02, 2)
        stop_loss = ma20 or round(price * 0.92, 2)
        add_position = round(price * 1.05, 2)
        tp_short = round(price * 1.08, 2)
        tp_mid = round(price * 1.15, 2)
        tp_long = round(price * 1.25, 2)

        findings.append(f"💰 当前价格：{price:.2f}（今日 {pct:+.2f}%）")
        findings.append(f"📍 最优入场区间：{entry_low} ~ {entry_high}")
        findings.append(f"📍 二次加仓点：{add_position}（突破确认后）")
        findings.append(f"🛑 强制止损位：{stop_loss}（MA20硬止损）")
        findings.append(f"🎯 止盈目标：短线{tp_short}（+8%）| 中线{tp_mid}（+15%）| 长线{tp_long}（+25%）")

    # ── 仓位建议 ──
    if total_score >= 85:
        position = "30-40%重点配置"
    elif total_score >= 75:
        position = "20-30%标准配置"
    elif total_score >= 65:
        position = "10-15%轻仓试探"
    elif total_score >= 55:
        position = "5%试仓观察"
    else:
        position = "空仓观望，暂不建仓"

    findings.append(f"📦 建议仓位：{position}")

    # ── 三周期操作策略 ──
    m06 = module_results.get("M06")
    tech_detail = m06.detail if m06 else {}

    short_advice = (
        f"短线（1-7日）：入场区间 {fmt(price)}±2%，"
        f"止损 {fmt(tech_detail.get('stop_loss') or (ma20 if ma20 else None))}，"
        f"止盈 {fmt(tech_detail.get('take_profit_1') or (round(price * 1.08, 2) if price else None))}"
    )
    mid_advice = (
        f"中线（1-3月）：MA20（{fmt(ma20)}）为多空分界，站稳可持有，"
        f"目标 {fmt(tech_detail.get('take_profit_2') or (round(price * 1.15, 2) if price else None))}"
    )
    long_advice = (
        f"长线（6-12月）：{rating_name}评级，"
        f"{'建议长线持有，每季复核基本面' if total_score >= 70 else '基本面支撑不足，不建议长线持有'}"
    )

    # ── 核心亮点与风险提示 ──
    highlights = []
    risks = []

    for mid in ["M01", "M02", "M04", "M05"]:
        r = module_results.get(mid)
        if r and r.score >= 8 and r.key_findings:
            for f in r.key_findings:
                if "✅" in f:
                    highlights.append(f.replace("✅ ", ""))
                    break

    for mid in ["M02", "M03", "M05", "M14"]:
        r = module_results.get(mid)
        if r and r.score < 5 and r.key_findings:
            for f in r.key_findings:
                if "⚠️" in f or "🚨" in f:
                    risks.append(f.replace("⚠️ ", "").replace("🚨 ", ""))
                    break

    if highlights:
        findings.append(f"✅ 核心亮点：{' | '.join(highlights[:3])}")
    if risks:
        findings.append(f"⚠️ 核心风险：{' | '.join(risks[:3])}")

    # ── 动态跟踪方案 ──
    findings.append("📋 动态跟踪：")
    if price and ma20:
        findings.append(f"  → 加仓触发：站稳MA20（{ma20:.2f}）且成交量放大")
        findings.append(f"  → 止盈触发：RSI>75或涨幅超过15%分批兑现")
        findings.append(f"  → 止损触发：跌破MA20（{ma20:.2f}）减仓，跌破-12%清仓")
        findings.append("  → 波段做T：高抛低吸MA10与MA20之间的区间")

    conclusion = f"综合评分 {total_score:.1f}分，{stars}星{rating_name}，{risk_level}。{position}策略。"

    return ModuleResult(
        module_id="M16",
        module_name="多维加权综合投资策略总结",
        score=round(total_score / 10, 1),  # 10分制
        stars=stars,
        key_findings=findings,
        short_advice=short_advice,
        mid_advice=mid_advice,
        long_advice=long_advice,
        conclusion=conclusion,
        detail={
            "total_score": total_score,
            "stars": stars,
            "rating_name": rating_name,
            "risk_level": risk_level,
            "color": color,
            "position": position,
            "ma10": ma10,
            "ma20": ma20,
            "price": price,
            "highlights": highlights,
            "risks": risks,
        },
    )
