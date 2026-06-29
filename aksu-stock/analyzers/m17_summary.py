"""M17 — 多维加权综合投资策略总结（100分制）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, pct_str, fmt_number


# 权重配置（同 SKILL.md 说明）
WEIGHTS = {
    "fundamental": {
        "modules": ["M01", "M02", "M03"],
        "weight": 0.30,
    },
    "industry_valuation": {
        "modules": ["M04", "M05"],
        "weight": 0.25,
    },
    "market_game": {
        "modules": ["M06", "M07", "M08", "M09"],
        "weight": 0.25,
    },
    "risk_catalyst": {
        "modules": ["M10", "M11", "M12", "M13", "M14"],
        "weight": 0.20,
    },
}


def _dim_avg(module_results: dict, module_ids: list[str]) -> float:
    scores = [module_results[mid].score for mid in module_ids if mid in module_results]
    return sum(scores) / len(scores) if scores else 5.0


def analyze_summary(data: dict, module_results: dict) -> ModuleResult:
    code = data.get("code", "")
    name = data.get("name") or code
    price = safe_float(data.get("price"))

    # ── 综合投资价值评分（100分制）──
    dim_fund = _dim_avg(module_results, WEIGHTS["fundamental"]["modules"])
    dim_iv = _dim_avg(module_results, WEIGHTS["industry_valuation"]["modules"])
    dim_mg = _dim_avg(module_results, WEIGHTS["market_game"]["modules"])
    dim_rc = _dim_avg(module_results, WEIGHTS["risk_catalyst"]["modules"])

    raw_score = (
        dim_fund * WEIGHTS["fundamental"]["weight"] +
        dim_iv * WEIGHTS["industry_valuation"]["weight"] +
        dim_mg * WEIGHTS["market_game"]["weight"] +
        dim_rc * WEIGHTS["risk_catalyst"]["weight"]
    )
    # 归一到100分制（1-10 → 0-100，但基准是5=50分）
    total_score = round((raw_score - 1) / 9 * 100, 1)
    total_score = max(0.0, min(100.0, total_score))

    # 星级
    if total_score >= 90:
        stars = 5
        rating_name = "极具投资价值"
        rating_color = "deep-green"
        position = "核心仓位60%-80%"
    elif total_score >= 80:
        stars = 4
        rating_name = "优质标的"
        rating_color = "light-green"
        position = "标准仓位40%-60%"
    elif total_score >= 70:
        stars = 3
        rating_name = "中性震荡"
        rating_color = "yellow"
        position = "轻仓观察20%-30%"
    elif total_score >= 60:
        stars = 2
        rating_name = "偏弱谨慎"
        rating_color = "orange"
        position = "仓位上限20%"
    else:
        stars = 1
        rating_name = "规避离场"
        rating_color = "red"
        position = "不建议持仓"

    # ── 现价择时评分 ──
    m16 = module_results.get("M16")
    timing_score = m16.detail.get("timing_score", 50) if m16 else 50.0
    timing_level = m16.detail.get("timing_level", "—") if m16 else "—"
    timing_operation = m16.detail.get("operation", "—") if m16 else "—"

    # ── 风控参数 ──
    m14 = module_results.get("M14")
    stop_loss = m14.detail.get("stop_loss") if m14 else None
    take_profit_1 = m14.detail.get("take_profit_1") if m14 else None
    take_profit_2 = m14.detail.get("take_profit_2") if m14 else None
    risk_reward = m14.detail.get("risk_reward") if m14 else None
    risk_items = m14.detail.get("risk_items", []) if m14 else []
    leverage_warning = m14.detail.get("leverage_warning", "") if m14 else ""

    # ── 估值区间 ──
    m05 = module_results.get("M05")
    valuation_zone = m05.detail.get("valuation_zone", "—") if m05 else "—"
    pe_ttm = safe_float(data.get("pe_ttm"))

    # ── 同业对标 ──
    m15 = module_results.get("M15")
    substitutes = m15.detail.get("substitutes", "") if m15 else ""
    comparison_rows = m15.detail.get("comparison_rows", []) if m15 else []

    # ── 资金阶段 ──
    m07 = module_results.get("M07")
    fund_stage = m07.detail.get("stage", "—") if m07 else "—"

    # ── 技术关键位 ──
    m06 = module_results.get("M06")
    support = m06.detail.get("support") if m06 else None
    resistance = m06.detail.get("resistance") if m06 else None

    # ── 核心亮点（从各模块提取最高分模块的第一条发现）──
    sorted_modules = sorted(
        [(mid, r) for mid, r in module_results.items() if mid not in ("M16", "M17")],
        key=lambda x: x[1].score, reverse=True
    )
    highlights = []
    for mid, r in sorted_modules[:3]:
        if r.key_findings:
            highlights.append(f"【{r.module_name}】{r.key_findings[0]}")

    # ── 核心风险（从低分模块提取）──
    core_risks = [item for item in risk_items if "致命" in item or "严重" in item or "⚠️" in item][:3]
    if not core_risks:
        lowest_modules = sorted_modules[-3:][::-1]
        for mid, r in lowest_modules:
            if r.key_findings:
                for f in r.key_findings:
                    if "⚠️" in f:
                        core_risks.append(f)
                        break
    if not core_risks:
        core_risks = ["当前暂无重大风险，需持续跟踪基本面变化"]

    # ── 三周期策略 ──
    short_ops = []
    mid_ops = []
    long_ops = []
    for _, r in sorted_modules[:5]:
        if r.short_advice and r.short_advice not in short_ops:
            short_ops.append(r.short_advice)
        if r.mid_advice and r.mid_advice not in mid_ops:
            mid_ops.append(r.mid_advice)
        if r.long_advice and r.long_advice not in long_ops:
            long_ops.append(r.long_advice)

    # ── 动态持仓跟踪方案 ──
    add_condition = f"加仓触发：价格突破 {fmt_number(resistance, 2)} 且成交量>均量1.5倍"
    stop_condition = f"止损触发：价格跌破 {fmt_number(stop_loss, 2)}，当日收盘确认"
    profit_condition = f"止盈触发：价格到达 {fmt_number(take_profit_1, 2)} 减半仓，到达 {fmt_number(take_profit_2, 2)} 清仓"
    swing_condition = f"做T策略：{'高抛低吸，以MA5为短线边界，每次T差≥2%' if timing_score >= 65 else '当前择时分低，暂停做T，全仓持有或规避'}"

    findings = [
        f"综合投资价值评分：{total_score:.1f}/100 {'★'*stars}{'☆'*(5-stars)} — {rating_name}",
        f"现价交易择时评分：{timing_score:.1f}/100 — {timing_level}",
        f"建议仓位：{position}",
        *highlights[:3],
        *core_risks[:2],
    ]

    return ModuleResult(
        module_id="M17",
        module_name="多维加权综合投资策略总结",
        score=min(10.0, total_score / 10),
        stars=stars,
        key_findings=findings[:8],
        short_advice=short_ops[0] if short_ops else timing_operation,
        mid_advice=mid_ops[0] if mid_ops else f"中线：{valuation_zone}区间，{position}",
        long_advice=long_ops[0] if long_ops else f"长线：{'核心资产长期持有' if stars >= 4 else '普通标的，跟踪基本面'}",
        conclusion=f"综合评分 {total_score:.1f}/100 {rating_name}，择时评分 {timing_score:.1f}/100 {timing_level}",
        detail={
            "total_score": total_score,
            "stars": stars,
            "rating_name": rating_name,
            "rating_color": rating_color,
            "position": position,
            "timing_score": timing_score,
            "timing_level": timing_level,
            "timing_color": m16.detail.get("timing_color", "orange") if m16 else "orange",
            "timing_operation": timing_operation,
            "valuation_zone": valuation_zone,
            "fund_stage": fund_stage,
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "risk_reward": risk_reward,
            "leverage_warning": leverage_warning,
            "highlights": highlights,
            "core_risks": core_risks,
            "support": support,
            "resistance": resistance,
            "add_condition": add_condition,
            "stop_condition": stop_condition,
            "profit_condition": profit_condition,
            "swing_condition": swing_condition,
            "comparison_rows": comparison_rows,
            "substitutes": substitutes,
            "dim_scores": {
                "基本面": round(dim_fund, 2),
                "行业估值": round(dim_iv, 2),
                "市场博弈": round(dim_mg, 2),
                "风控催化": round(dim_rc, 2),
            },
        },
    )
