"""M03 — 股权治理与股东行为评估（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str


def analyze_governance(data: dict) -> ModuleResult:
    top10 = data.get("top10_holders") or []
    pledge_ratio = safe_float(data.get("pledge_ratio"))
    holder_num = safe_float(data.get("holder_num"))
    holder_num_change_pct = safe_float(data.get("holder_num_change_pct"))
    north_fund = data.get("north_fund") or {}
    research_reports = data.get("research_reports") or []

    findings: list[str] = []

    # ── 股权稳定性（3分）──
    score_stability = 1.5
    if pledge_ratio is not None:
        if pledge_ratio < 5:
            score_stability = 3.0
            findings.append(f"质押比例极低（{pct_str(pledge_ratio)}），股权风险可控")
        elif pledge_ratio < 20:
            score_stability = 2.5
            findings.append(f"质押比例适中（{pct_str(pledge_ratio)}），关注质押触发线")
        elif pledge_ratio < 40:
            score_stability = 1.5
            findings.append(f"⚠️ 质押比例偏高（{pct_str(pledge_ratio)}），存在质押爆仓风险")
        else:
            score_stability = 0.8
            findings.append(f"⚠️ 质押比例极高（{pct_str(pledge_ratio)}），爆仓风险高，需重点关注")
    else:
        findings.append("质押比例数据暂缺，建议通过年报核实")

    # ── 股东行为正面度（3分）──
    score_behavior = 1.5
    if top10:
        institution_count = sum(1 for h in top10 if any(
            kw in str(h.get("holder_type", "")) for kw in ["基金", "机构", "险", "QFII"]
        ))
        if institution_count >= 5:
            score_behavior = 3.0
            findings.append(f"前十大流通股东中机构数量 {institution_count} 家，机构持仓高度集中，认可度强")
        elif institution_count >= 3:
            score_behavior = 2.5
            findings.append(f"前十大流通股东中有 {institution_count} 家机构，机构布局明显")
        else:
            score_behavior = 2.0
            findings.append(f"前十大流通股东机构持仓 {institution_count} 家，机构认可度一般")
        # 股东人数变化分析
        if holder_num_change_pct is not None:
            if holder_num_change_pct < -5:
                score_behavior = min(score_behavior + 0.3, 3.0)
                findings.append(f"股东人数减少 {abs(holder_num_change_pct):.1f}%，筹码集中趋势，利多")
            elif holder_num_change_pct > 10:
                score_behavior = max(score_behavior - 0.3, 0.5)
                findings.append(f"⚠️ 股东人数增加 {holder_num_change_pct:.1f}%，筹码趋于分散，注意风险")
    else:
        findings.append("⚠️ 前十大股东数据获取失败，建议手动查询东方财富股东界面")

    # ── 治理规范性（2分）──
    score_governance = 1.8
    findings.append("治理规范性需结合年报、监管问询、违规处罚记录综合判断")

    # ── 机构认可度（2分）──
    score_institution = 1.5
    north_hold_ratio = safe_float((north_fund or {}).get("hold_ratio"))
    if north_hold_ratio is not None:
        if north_hold_ratio > 5:
            score_institution = 2.0
            findings.append(f"北向资金持股比例 {pct_str(north_hold_ratio)}，外资高度认可")
        elif north_hold_ratio > 2:
            score_institution = 1.8
            findings.append(f"北向资金持股 {pct_str(north_hold_ratio)}，有一定外资配置")
        else:
            score_institution = 1.5
            findings.append(f"北向资金持股 {pct_str(north_hold_ratio)}，外资关注度有限")
    if research_reports:
        score_institution = min(score_institution + 0.2, 2.0)

    total = score_stability + score_behavior + score_governance + score_institution
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M03",
        module_name="股权治理与股东行为评估",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice="短线：关注大股东增减持公告，警惕解禁减持窗口",
        mid_advice="中线：跟踪机构持仓季报变动，股东人数持续减少是积极信号",
        long_advice="长线：质押比例>40%是核心风险，长期持仓须保持低质押",
        conclusion=f"股权治理评分 {total:.1f}/10，质押比例 {pct_str(pledge_ratio)}，机构持仓{'良好' if score_institution >= 1.8 else '一般'}",
        detail={
            "pledge_ratio": pledge_ratio,
            "holder_num": holder_num,
            "holder_num_change_pct": holder_num_change_pct,
            "top10_count": len(top10),
        },
    )
