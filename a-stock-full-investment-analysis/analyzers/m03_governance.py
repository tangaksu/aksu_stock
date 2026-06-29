"""M03 股权治理与股东行为评估"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt


def analyze_governance(data: dict) -> ModuleResult:
    holders = data.get("top10_holders") or []
    pledge = data.get("pledge_ratio") or {}
    holder_num = data.get("holder_num") or {}
    mgmt = data.get("management_changes") or []

    findings = []
    warnings = []
    score = 6.0  # 基础分

    # ── 股权质押风险 ──
    pledge_ratio = pledge.get("pledge_ratio")
    if pledge_ratio is not None:
        findings.append(f"股权质押比例：{fmt(pledge_ratio)}%")
        if pledge_ratio >= 50:
            score -= 2.5
            warnings.append(f"🚨 质押比例高达 {pledge_ratio:.1f}%，爆仓平仓风险极高")
        elif pledge_ratio >= 30:
            score -= 1.5
            warnings.append(f"⚠️ 质押比例 {pledge_ratio:.1f}%，存在较大平仓压力")
        elif pledge_ratio >= 10:
            score -= 0.5
            findings.append(f"⚠️ 质押比例 {pledge_ratio:.1f}%，需关注")
        else:
            score += 0.5
            findings.append("✅ 质押比例低，股权稳定无平仓风险")

    # ── 股东人数变化（筹码集中度） ──
    h_num = holder_num.get("holder_num")
    h_prev = holder_num.get("holder_num_prev")
    h_pct = holder_num.get("holder_num_change_pct")
    if h_num and h_prev:
        findings.append(f"最新股东人数：{h_num:,}，环比变化：{h_pct:+.2f}%")
        if h_pct and h_pct < -5:
            score += 1.0
            findings.append("✅ 股东人数减少，筹码向主力集中，看多信号")
        elif h_pct and h_pct > 10:
            score -= 0.5
            findings.append("⚠️ 股东人数大增，筹码分散，上涨动力减弱")

    # ── 前十大流通股东 ──
    if holders:
        # 检查机构持股
        institutional = [h for h in holders if any(k in h.get("name", "") for k in
                          ["基金", "社保", "保险", "QFII", "北向", "ETF", "信托"])]
        findings.append(f"前十大流通股东数量：{len(holders)} 家")
        if institutional:
            score += 1.0
            findings.append(f"✅ 机构持仓明显（{len(institutional)} 家机构），基本面认可度高")

        # 检查北向持仓
        north = [h for h in holders if "香港" in h.get("name", "") or "北向" in h.get("name", "")]
        if north:
            score += 0.5
            findings.append("✅ 北向资金持股，国际资本认可")

        # 前十大合计持股比例
        ratios = [h.get("ratio") or 0 for h in holders if h.get("ratio")]
        if ratios:
            total_ratio = sum(ratios)
            findings.append(f"前十大合计持股：{total_ratio:.2f}%")
            if total_ratio > 60:
                score += 0.5
                findings.append("✅ 筹码高度集中，主力控盘")
            elif total_ratio < 30:
                findings.append("⚠️ 股权分散，机构持仓较低")

    # ── 高管增减持 ──
    if mgmt:
        buy_mgmt = [m for m in mgmt if "增持" in m.get("change_type", "") or "买入" in m.get("change_type", "")]
        sell_mgmt = [m for m in mgmt if "减持" in m.get("change_type", "") or "卖出" in m.get("change_type", "")]

        if buy_mgmt:
            score += 1.0
            findings.append(f"✅ 近期高管增持 {len(buy_mgmt)} 次，内部人看多信号")
        if sell_mgmt:
            score -= 0.5
            count = len(sell_mgmt)
            if count >= 3:
                score -= 1.0
                warnings.append(f"⚠️ 近期高管减持 {count} 次，需关注离场原因")
            else:
                findings.append(f"ℹ️ 近期高管减持 {count} 次，属正常范围")

    score = min(10.0, max(1.0, score))
    all_findings = findings + warnings

    conclusion = (
        f"股权治理整体评分 {score:.1f}/10。"
        + (warnings[0] if warnings else "股权稳定，股东行为未见异常减持信号。")
    )

    return ModuleResult(
        module_id="M03",
        module_name="股权治理与股东行为评估",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice="关注近期解禁计划与高管减持公告，防范突发抛压",
        mid_advice="机构持仓增加与股东人数下降同步出现时，中线做多信号明确",
        long_advice="股权质押率低、管理层持续增持的企业，长线持有风险更小",
        conclusion=conclusion,
        detail={"pledge": pledge, "holder_num": holder_num, "management": mgmt},
    )
