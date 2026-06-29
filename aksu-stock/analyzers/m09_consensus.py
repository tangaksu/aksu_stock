"""M09 — 市场分歧与机构预期统计（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_consensus(data: dict) -> ModuleResult:
    analyst_ratings = data.get("analyst_ratings") or {}
    research_reports = data.get("research_reports") or []
    avg_target_price = safe_float(data.get("avg_target_price"))
    price = safe_float(data.get("price"))
    pe_ttm = safe_float(data.get("pe_ttm"))
    profit_yoy = safe_float(data.get("profit_yoy"))

    findings: list[str] = []

    # ── 机构共识度（3分）──
    score_consensus = 1.5
    ratings = analyst_ratings.get("ratings") or {}
    total_reports = analyst_ratings.get("total_reports") or 0
    if total_reports > 0:
        buy_count = ratings.get("买入", 0) + ratings.get("增持", 0)
        sell_count = ratings.get("卖出", 0) + ratings.get("减持", 0)
        bull_ratio = buy_count / total_reports
        findings.append(
            f"近期机构研报 {total_reports} 篇：买入/增持 {buy_count} 篇，"
            f"中性 {ratings.get('中性', 0)} 篇，"
            f"减持/卖出 {sell_count} 篇，看多比例 {pct_str(bull_ratio*100)}"
        )
        if bull_ratio > 0.8:
            score_consensus = 3.0
            findings.append("机构高度一致看多，共识度强")
        elif bull_ratio > 0.6:
            score_consensus = 2.5
            findings.append("机构整体偏多，共识度良好")
        elif bull_ratio > 0.4:
            score_consensus = 2.0
            findings.append("机构分歧较大，多空相对均衡")
        else:
            score_consensus = 1.0
            findings.append("⚠️ 机构整体偏空，需关注基本面恶化风险")
    elif research_reports:
        score_consensus = 1.8
        findings.append(f"获取到 {len(research_reports)} 篇研报，但评级统计不完整，具体评级需手动核实")
    else:
        findings.append("⚠️ 机构研报数据暂缺，建议在东方财富/同花顺研报中心查询")

    # ── 预期差空间（4分）──
    score_expectation = 2.0
    if avg_target_price and price and price > 0:
        upside = (avg_target_price - price) / price * 100
        findings.append(f"机构平均目标价 {fmt_number(avg_target_price, 2)}，较现价潜在空间 {pct_str(upside)}")
        if upside > 50:
            score_expectation = 4.0
            findings.append("机构一致看多，目标价大幅高于现价，预期差空间极大")
        elif upside > 30:
            score_expectation = 3.5
            findings.append("机构目标价显著高于现价，预期差空间大")
        elif upside > 15:
            score_expectation = 3.0
            findings.append("机构目标价适度高于现价，有上涨空间")
        elif upside > 0:
            score_expectation = 2.5
            findings.append("机构目标价小幅高于现价，上涨空间有限")
        elif upside > -15:
            score_expectation = 2.0
            findings.append("机构目标价接近现价，预期差空间不大")
        else:
            score_expectation = 1.0
            findings.append(f"⚠️ 机构目标价低于现价，下行风险较大")
    else:
        # 用PE和业绩增速估算预期差
        if pe_ttm and pe_ttm > 0 and profit_yoy and profit_yoy > 0:
            peg = pe_ttm / profit_yoy
            if peg < 0.8:
                score_expectation = 3.5
                findings.append(f"PEG {peg:.2f}（<0.8），市场明显低估业绩增长，预期差空间大")
            elif peg < 1.2:
                score_expectation = 2.5
                findings.append(f"PEG {peg:.2f}（合理区间），市场预期与业绩增速基本匹配")
            else:
                score_expectation = 1.5
                findings.append(f"PEG {peg:.2f}（>1.2），市场已充分甚至过度定价增长预期")
        else:
            findings.append("机构目标价数据暂缺，预期差分析基于公开数据估算")

    # ── 研报催化潜力（3分）──
    score_catalyst = 1.5
    if len(research_reports) >= 10:
        score_catalyst = 3.0
        findings.append(f"近期研报数量 {len(research_reports)} 篇，机构覆盖密集，关注度极高，研报催化效应强")
    elif len(research_reports) >= 5:
        score_catalyst = 2.5
        findings.append(f"近期研报 {len(research_reports)} 篇，机构覆盖良好，有一定研报催化潜力")
    elif len(research_reports) >= 2:
        score_catalyst = 2.0
        findings.append(f"近期研报 {len(research_reports)} 篇，机构覆盖一般")
    elif len(research_reports) >= 1:
        score_catalyst = 1.8
        # 展示最新一篇研报
        rpt = research_reports[0]
        findings.append(f"最新研报：{rpt.get('org', '—')}《{rpt.get('title', '—')[:30]}》评级:{rpt.get('rating', '—')}")
    else:
        findings.append("近期无机构覆盖研报，市场关注度低，研报催化潜力不足")

    total = score_consensus + score_expectation + score_catalyst
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M09",
        module_name="市场分歧与机构预期",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice=f"短线：机构研报{'密集发布期，可跟催化' if len(research_reports) >= 5 else '稀少，依赖技术面操作'}",
        mid_advice=f"中线：{'机构目标价显示' + pct_str((avg_target_price - price) / price * 100 if avg_target_price and price else 0) + '上行空间，可中线持有' if avg_target_price and price and avg_target_price > price else '关注机构预期差变化'}",
        long_advice="长线：机构评级下调是减仓信号，核心逻辑不变时维持持仓",
        conclusion=f"机构预期评分 {total:.1f}/10，研报 {len(research_reports)} 篇，{'看多为主' if score_consensus >= 2.5 else '分歧较大' if score_consensus >= 1.8 else '看空为主'}",
        detail={
            "total_reports": total_reports,
            "avg_target_price": avg_target_price,
            "research_count": len(research_reports),
            "bull_ratio": (ratings.get("买入", 0) + ratings.get("增持", 0)) / max(total_reports, 1),
        },
    )
