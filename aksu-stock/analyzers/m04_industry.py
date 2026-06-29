"""M04 — 行业周期与产业链景气度分析（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str


def analyze_industry(data: dict) -> ModuleResult:
    industry = data.get("industry") or "未知行业"
    industry_peers = data.get("industry_peers") or []
    pct_change = safe_float(data.get("pct_change"))
    research_reports = data.get("research_reports") or []

    findings: list[str] = []

    # ── 行业景气度与持续性（3分）──
    score_prosperity = 1.5
    if industry_peers:
        peer_pcts = [safe_float(p.get("pct_change")) for p in industry_peers if safe_float(p.get("pct_change")) is not None]
        if peer_pcts:
            avg_pct = sum(peer_pcts) / len(peer_pcts)
            findings.append(f"行业同日平均涨跌 {pct_str(avg_pct)}，共 {len(industry_peers)} 家同业标的")
            if avg_pct > 2:
                score_prosperity = 3.0
                findings.append("行业今日表现强势，景气度较高")
            elif avg_pct > 0:
                score_prosperity = 2.0
                findings.append("行业今日小幅上涨，景气度平稳")
            elif avg_pct < -2:
                score_prosperity = 1.0
                findings.append("⚠️ 行业整体下跌，景气度承压")
    else:
        findings.append(f"所属行业：{industry}，行业整体景气度数据获取中")

    # ── 政策红利力度（2分）──
    score_policy = 1.5
    # 从研报标题中提取政策关键词
    policy_keywords = ["政策", "补贴", "支持", "利好", "扶持", "规划", "指导"]
    policy_reports = [r for r in research_reports if any(kw in r.get("title", "") for kw in policy_keywords)]
    if policy_reports:
        score_policy = 2.0
        findings.append(f"近期 {len(policy_reports)} 篇研报涉及政策利好，政策驱动力较强")
    else:
        findings.append("政策面：暂无明显研报政策利好信号，关注宏观政策走向")

    # ── 产业链供需优势（3分）──
    score_supply_demand = 1.5
    pe_values = [safe_float(p.get("pe_ttm")) for p in industry_peers if safe_float(p.get("pe_ttm"))]
    if pe_values:
        avg_pe = sum(v for v in pe_values if v and v > 0) / max(1, sum(1 for v in pe_values if v and v > 0))
        findings.append(f"行业平均PE（同业均值） {avg_pe:.1f}x，反映市场对行业供需预期")
        if 10 < avg_pe < 30:
            score_supply_demand = 2.5
        elif avg_pe <= 10:
            score_supply_demand = 3.0
            findings.append("行业估值较低，产业链可能处于底部修复阶段")
        else:
            score_supply_demand = 1.5
            findings.append("行业估值偏高，需关注景气度是否可持续")
    else:
        findings.append("产业链供需数据需结合上下游库存周期综合判断")

    # ── 行业格局集中度（2分）──
    score_concentration = 1.8
    if industry_peers:
        cap_values = [safe_float(p.get("market_cap")) for p in industry_peers if safe_float(p.get("market_cap"))]
        if cap_values:
            total_cap = sum(v for v in cap_values if v)
            top3_cap = sum(sorted([v for v in cap_values if v], reverse=True)[:3])
            cr3 = top3_cap / total_cap * 100 if total_cap else 0
            findings.append(f"行业前3名市值集中度 CR3 = {cr3:.1f}%，{'集中度高，龙头效应明显' if cr3 > 50 else '竞争格局较分散'}")
            score_concentration = 2.0 if cr3 > 50 else 1.5

    total = score_prosperity + score_policy + score_supply_demand + score_concentration
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M04",
        module_name="行业周期与产业链景气度",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice=f"短线：关注【{industry}】板块资金轮动，跟踪当日涨停板效应",
        mid_advice="中线：关注行业景气度拐点信号，跟踪上游成本变化与下游需求数据",
        long_advice="长线：判断行业处于生命周期哪个阶段（成长/成熟/衰退），选择扩张期布局",
        conclusion=f"行业景气度评分 {total:.1f}/10，所属【{industry}】，建议关注板块政策驱动与龙头效应",
        detail={
            "industry": industry,
            "peer_count": len(industry_peers),
            "policy_report_count": len([r for r in research_reports if any(
                kw in r.get("title", "") for kw in ["政策", "补贴", "支持", "利好"]
            )]),
        },
    )
