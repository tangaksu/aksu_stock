"""M07 — 资金筹码深度博弈分析（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_capital(data: dict) -> ModuleResult:
    main_net_inflow = safe_float(data.get("main_net_inflow"))
    super_large_inflow = safe_float(data.get("super_large_inflow"))
    large_inflow = safe_float(data.get("large_inflow"))
    main_net_ratio = safe_float(data.get("main_net_ratio"))
    fund_flow = data.get("fund_flow") or {}
    north_fund = data.get("north_fund") or {}
    dragon_tiger = data.get("dragon_tiger") or []
    holder_num = safe_float(data.get("holder_num"))
    holder_num_change_pct = safe_float(data.get("holder_num_change_pct"))
    turnover_rate = safe_float(data.get("turnover_rate"))

    findings: list[str] = []

    # ── 主力资金认可度（3分）──
    score_main = 1.5
    if main_net_inflow is not None:
        inflow_wan = main_net_inflow / 10000 if abs(main_net_inflow) > 10000 else main_net_inflow
        unit = "亿" if abs(main_net_inflow) > 1e8 else "万"
        display_val = main_net_inflow / 1e8 if abs(main_net_inflow) > 1e8 else main_net_inflow / 1e4
        if main_net_inflow > 5e7:
            score_main = 3.0
            findings.append(f"主力大幅净流入 {display_val:.2f}{unit}，机构资金强烈认可")
        elif main_net_inflow > 1e7:
            score_main = 2.5
            findings.append(f"主力净流入 {display_val:.2f}{unit}，资金积极布局")
        elif main_net_inflow > 0:
            score_main = 2.0
            findings.append(f"主力小幅净流入 {display_val:.2f}{unit}，资金温和看多")
        elif main_net_inflow > -1e7:
            score_main = 1.5
            findings.append(f"主力小幅净流出 {abs(display_val):.2f}{unit}，资金观望为主")
        elif main_net_inflow > -5e7:
            score_main = 1.0
            findings.append(f"⚠️ 主力净流出 {abs(display_val):.2f}{unit}，需关注资金出逃迹象")
        else:
            score_main = 0.5
            findings.append(f"⚠️ 主力大幅净流出 {abs(display_val):.2f}{unit}，资金加速离场，谨慎")
    else:
        findings.append("⚠️ 主力资金流向数据获取失败，需手动查询东方财富资金流向")

    if super_large_inflow is not None and super_large_inflow > 0:
        findings.append(f"超大单净流入，机构/游资主动买入信号明确")
    if main_net_ratio is not None:
        findings.append(f"主力净流入占比 {pct_str(main_net_ratio)}（{'强势' if main_net_ratio > 5 else '中性'}）")

    # ── 资金流入持续性（2分）──
    score_continuity = 1.0
    recent = (fund_flow or {}).get("recent_5days") or []
    if recent:
        positive_days = sum(1 for d in recent if safe_float(d.get("主力净流入净额")) and safe_float(d.get("主力净流入净额")) > 0)
        findings.append(f"近5日资金：连续净流入 {positive_days} 天（共5日）")
        if positive_days >= 4:
            score_continuity = 2.0
        elif positive_days >= 3:
            score_continuity = 1.7
        elif positive_days >= 2:
            score_continuity = 1.3
        else:
            score_continuity = 0.8

    # ── 筹码稳定度（3分）──
    score_chip = 1.5
    if holder_num_change_pct is not None:
        if holder_num_change_pct < -10:
            score_chip = 3.0
            findings.append(f"股东人数减少 {abs(holder_num_change_pct):.1f}%，筹码高度集中，主力锁仓明显")
        elif holder_num_change_pct < -5:
            score_chip = 2.5
            findings.append(f"股东人数减少 {abs(holder_num_change_pct):.1f}%，筹码集中趋势良好")
        elif holder_num_change_pct < 0:
            score_chip = 2.0
            findings.append(f"股东人数小幅减少 {abs(holder_num_change_pct):.1f}%，筹码趋于集中")
        elif holder_num_change_pct > 10:
            score_chip = 1.0
            findings.append(f"⚠️ 股东人数增加 {holder_num_change_pct:.1f}%，筹码分散，持仓不稳定")
        else:
            score_chip = 1.5
            findings.append(f"股东人数变化 {pct_str(holder_num_change_pct)}，筹码变动平稳")

    # ── 主力控盘度（2分）──
    score_control = 1.0
    if dragon_tiger:
        net_values = [safe_float(d.get("net")) for d in dragon_tiger if safe_float(d.get("net")) is not None]
        if net_values:
            total_net = sum(v for v in net_values if v)
            if total_net > 0:
                score_control = 2.0
                findings.append(f"龙虎榜净买入，主力资金入场意图明确")
            else:
                score_control = 0.8
                findings.append(f"⚠️ 龙虎榜净卖出，警惕主力出货")
    else:
        # 通过换手率间接判断
        if turnover_rate is not None:
            if 2 < turnover_rate < 8:
                score_control = 1.5
                findings.append("换手率适中，主力控盘状态正常")
            elif turnover_rate > 15:
                score_control = 0.8
                findings.append("⚠️ 换手率过高，筹码混乱，主力控盘度低")

    total = score_main + score_continuity + score_chip + score_control
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    # 判断主力操盘阶段
    if score_chip >= 2.5 and score_main >= 2.0 and score_control >= 1.5:
        stage = "洗盘/建仓末期"
    elif score_main >= 2.5 and score_continuity >= 1.5:
        stage = "拉升期"
    elif score_main <= 1.0 and score_continuity <= 1.0:
        stage = "派发期"
    else:
        stage = "观望整理"

    return ModuleResult(
        module_id="M07",
        module_name="资金筹码深度博弈",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice=f"短线：{'主力净流入，可跟进' if main_net_inflow and main_net_inflow > 0 else '主力流出，谨慎参与'}",
        mid_advice=f"中线：操盘阶段判断为【{stage}】，{'持仓等待拉升' if stage in ['洗盘/建仓末期', '拉升期'] else '轻仓或离场'}",
        long_advice="长线：股东人数持续减少+主力连续净流入，是建立核心仓位的最佳信号",
        conclusion=f"资金博弈评分 {total:.1f}/10，主力操盘阶段：【{stage}】，主力净流入：{fmt_number((main_net_inflow or 0)/1e8, 2)}亿",
        detail={
            "main_net_inflow": main_net_inflow, "main_net_ratio": main_net_ratio,
            "holder_num_change_pct": holder_num_change_pct, "stage": stage,
            "dragon_tiger_count": len(dragon_tiger),
        },
    )
