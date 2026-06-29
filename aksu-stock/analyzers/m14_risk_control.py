"""M14 — 交易纪律与风控体系（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_risk_control(data: dict, module_results: dict | None = None) -> ModuleResult:
    price = safe_float(data.get("price"))
    ma20 = safe_float(data.get("ma20"))
    ma60 = safe_float(data.get("ma60"))
    boll = data.get("boll") or {}
    boll_lower = safe_float(boll.get("lower"))
    pe_ttm = safe_float(data.get("pe_ttm"))
    week52_low = safe_float(data.get("week52_low"))
    week52_high = safe_float(data.get("week52_high"))
    week52_position = safe_float(data.get("week52_position"))
    pledge_ratio = safe_float(data.get("pledge_ratio"))
    debt_ratio = safe_float(data.get("debt_ratio"))
    goodwill_ratio = safe_float(data.get("goodwill_ratio"))
    rsi14 = safe_float(data.get("rsi14"))
    main_net_inflow = safe_float(data.get("main_net_inflow"))

    findings: list[str] = []
    risk_items: list[str] = []  # 风险汇总

    # ── 风险收益比（3分）──
    score_rr = 1.5
    stop_loss = None
    take_profit_1 = None
    take_profit_2 = None
    risk_reward = None

    if price and ma20 and boll_lower:
        stop_loss = round(min(ma20 * 0.97, boll_lower * 0.995), 2)
    elif price and ma20:
        stop_loss = round(ma20 * 0.97, 2)
    elif price:
        stop_loss = round(price * 0.95, 2)

    if price and ma60:
        take_profit_1 = round(ma60 * 1.02, 2) if price < ma60 else round(price * 1.10, 2)
        take_profit_2 = round(price * 1.20, 2)

    if price and stop_loss and take_profit_1:
        risk = price - stop_loss
        reward = take_profit_1 - price
        if risk > 0 and reward > 0:
            risk_reward = round(reward / risk, 1)
            findings.append(f"风险收益比 = {risk_reward:.1f}:1（止损：{fmt_number(stop_loss, 2)}，止盈1：{fmt_number(take_profit_1, 2)}）")
            if risk_reward >= 3:
                score_rr = 3.0
                findings.append("盈亏比≥3:1，符合优质开仓标准")
            elif risk_reward >= 2:
                score_rr = 2.5
                findings.append(f"盈亏比{risk_reward}:1，基本符合开仓标准")
            elif risk_reward >= 1.5:
                score_rr = 2.0
                findings.append(f"盈亏比{risk_reward}:1，勉强接受，需精准选时")
            else:
                score_rr = 1.0
                risk_items.append(f"⚠️ 盈亏比{risk_reward}:1（<1.5），不建议在此位置开仓")

    # ── 风险可控度（4分）——汇总全维度风险点 ──
    score_risk = 3.5
    # 致命风险
    if pledge_ratio and pledge_ratio > 50:
        score_risk -= 1.0
        risk_items.append(f"【致命风险】质押比例 {pct_str(pledge_ratio)}，爆仓风险极高")
    if pe_ttm and pe_ttm > 80:
        score_risk -= 0.5
        risk_items.append(f"【中度风险】PE-TTM {pe_ttm:.0f}x，估值极高，泡沫破裂回调风险大")
    if debt_ratio and debt_ratio > 75:
        score_risk -= 0.5
        risk_items.append(f"【中度风险】负债率 {pct_str(debt_ratio)}，财务杠杆高，信用风险值得关注")
    if goodwill_ratio and goodwill_ratio > 20:
        score_risk -= 0.3
        risk_items.append(f"【轻微风险】商誉占总资产 {pct_str(goodwill_ratio)}，减值风险存在")
    if week52_position and week52_position > 85:
        score_risk -= 0.3
        risk_items.append(f"【轻微风险】52周高位（{week52_position:.0f}%），追高风险需注意")
    if rsi14 and rsi14 > 75:
        score_risk -= 0.2
        risk_items.append(f"【轻微风险】RSI {rsi14:.1f}，超买区，短期调整概率高")
    if main_net_inflow and main_net_inflow < -5e7:
        score_risk -= 0.3
        risk_items.append(f"【中度风险】主力持续净流出，资金离场信号")

    # 正面抵消
    if pledge_ratio and pledge_ratio < 5:
        score_risk = min(score_risk + 0.2, 4.0)
    if debt_ratio and debt_ratio < 30:
        score_risk = min(score_risk + 0.2, 4.0)

    score_risk = round(max(0.5, min(4.0, score_risk)), 2)

    if not risk_items:
        risk_items.append("当前未发现重大风险点，但需持续跟踪基本面与资金面变化")
    findings.extend(risk_items[:4])

    # ── 交易可执行性（3分）──
    score_exec = 2.0
    exec_plan: list[str] = []
    exec_plan.append(f"建议仓位：{'30%以下轻仓' if (week52_position or 50) > 70 or (rsi14 or 50) > 70 else '50%中仓' if score_risk >= 3 else '轻仓或观望'}")
    exec_plan.append(f"入场区间：{fmt_number(stop_loss * 1.01 if stop_loss else None, 2)} ~ {fmt_number(price, 2) if price else '—'}")
    exec_plan.append(f"强制止损：{fmt_number(stop_loss, 2)}（跌破立即执行，不拖单）")
    exec_plan.append(f"止盈目标1：{fmt_number(take_profit_1, 2)}（减半仓）")
    exec_plan.append(f"止盈目标2：{fmt_number(take_profit_2, 2)}（清仓）")
    findings.extend(exec_plan[:3])
    score_exec = 3.0 if stop_loss and take_profit_1 and risk_reward and risk_reward >= 2 else 2.0

    total = score_rr + score_risk + score_exec
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    # 杠杆警示
    leverage_warning = ""
    if week52_position and week52_position > 70:
        leverage_warning = "⚠️ 当前价格偏高，严禁使用杠杆，仓位上限30%"
    elif score_risk < 2.5:
        leverage_warning = "⚠️ 存在风险因素，禁止加杠杆，仓位控制在50%以内"

    return ModuleResult(
        module_id="M14",
        module_name="交易纪律与风控体系",
        score=total,
        stars=stars,
        key_findings=findings[:6],
        short_advice=f"止损：{fmt_number(stop_loss, 2)}，止盈目标：{fmt_number(take_profit_1, 2)}，{'立即执行止损不犹豫' if risk_reward and risk_reward < 1.5 else '严格执行计划'}",
        mid_advice=f"中线仓位上限：{'30%（高风险）' if score_risk < 2.5 else '50%（中等风险）' if score_risk < 3.5 else '60%（风险可控）'}，止损-3%触发减仓",
        long_advice=f"长线风控：{leverage_warning if leverage_warning else '基本面无恶化迹象可持仓，跌破年线考虑减仓'}",
        conclusion=f"风控评分 {total:.1f}/10，盈亏比 {fmt_number(risk_reward, 1)}:1，止损 {fmt_number(stop_loss, 2)}，{len([r for r in risk_items if '致命' in r])} 项致命风险",
        detail={
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "risk_reward": risk_reward,
            "risk_items": risk_items,
            "leverage_warning": leverage_warning,
        },
    )
