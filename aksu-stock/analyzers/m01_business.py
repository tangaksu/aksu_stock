"""M01 — 公司基础与业务拆解（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars


def analyze_business(data: dict) -> ModuleResult:
    code = data.get("code", "")
    name = data.get("name") or code
    industry = data.get("industry") or "未知行业"
    list_date = data.get("list_date") or "—"
    market_cap = safe_float(data.get("market_cap"))
    total_share = safe_float(data.get("total_share"))
    research_reports = data.get("research_reports") or []
    concepts = data.get("stock_concepts") or []

    findings: list[str] = []

    # 主营业务集中度（2分）
    score_concentration = 1.5
    findings.append(f"所属行业：{industry}，需结合年报确认主营业务集中度")

    # 价值链卡位（2分）
    score_value_chain = 1.5
    if research_reports:
        score_value_chain = 2.0
        findings.append(f"近期研报 {len(research_reports)} 篇，机构关注度较高，价值链卡位有研究支撑")
    else:
        findings.append("研报数量不足，价值链卡位评估依赖公开信息")

    # 核心壁垒厚度（2分）
    score_moat = 1.5
    if concepts:
        score_moat = 2.0
        findings.append(f"概念标签涵盖多个赛道，具备一定题材壁垒")

    # 业务稳定性（2分）
    score_stability = 1.5
    if list_date and list_date != "—":
        try:
            from datetime import datetime
            listed_year = int(str(list_date)[:4])
            years = datetime.now().year - listed_year
            if years >= 10:
                score_stability = 2.0
                findings.append(f"上市 {years} 年，经历多轮市场周期，业务稳定性较强")
            elif years >= 5:
                score_stability = 1.8
                findings.append(f"上市 {years} 年，具备一定历史沿革，稳定性中等")
            else:
                score_stability = 1.2
                findings.append(f"上市不足 5 年（{years}年），业务稳定性有待验证")
        except Exception:
            findings.append(f"上市日期：{list_date}")

    # 合规经营记录（2分）
    score_compliance = 1.8
    findings.append("合规记录需结合监管问询、违规处罚等公告核实")

    total = score_concentration + score_value_chain + score_moat + score_stability + score_compliance
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    cap_str = f"{market_cap/1e8:.1f}亿" if market_cap and market_cap > 1e8 else (f"{market_cap:.0f}" if market_cap else "—")

    return ModuleResult(
        module_id="M01",
        module_name="公司基础与业务拆解",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice="短线：关注近期公告与题材催化，确认主营无重大变化",
        mid_advice="中线：跟踪季报营收结构，判断业务集中度是否提升",
        long_advice="长线：深度研究护城河厚度，确认价值链卡位的可持续性",
        conclusion=f"{name}（{code}）属于【{industry}】赛道，总市值约{cap_str}，综合业务质量评分 {total:.1f}/10",
        detail={
            "industry": industry,
            "list_date": list_date,
            "market_cap": market_cap,
            "research_count": len(research_reports),
        },
    )
