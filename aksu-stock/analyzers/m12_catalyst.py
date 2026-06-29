"""M12 — 催化事件与前瞻预期分析（满分10分）"""
from __future__ import annotations
from datetime import datetime
from analyzers.base import ModuleResult, safe_float, score_to_stars


def analyze_catalyst(data: dict) -> ModuleResult:
    research_reports = data.get("research_reports") or []
    pledge_ratio = safe_float(data.get("pledge_ratio"))
    holder_num_change_pct = safe_float(data.get("holder_num_change_pct"))
    profit_yoy = safe_float(data.get("profit_yoy"))
    revenue_yoy = safe_float(data.get("revenue_yoy"))
    industry = data.get("industry") or "未知行业"
    dragon_tiger = data.get("dragon_tiger") or []

    findings: list[str] = []
    now = datetime.now()
    month = now.month

    # ── 催化事件数量（3分）──
    score_events = 1.5
    catalysts: list[str] = []

    # 业绩披露窗口
    if month in [1, 2]:
        catalysts.append("年报/业绩预告窗口（1-2月），重大业绩超预期概率高")
        score_events = min(score_events + 0.5, 3.0)
    elif month in [3, 4]:
        catalysts.append("年报+一季报集中披露期（3-4月），催化密集")
        score_events = min(score_events + 0.5, 3.0)
    elif month in [7, 8]:
        catalysts.append("半年报披露窗口（7-8月）")
        score_events = min(score_events + 0.3, 3.0)
    elif month in [10]:
        catalysts.append("三季报披露窗口（10月）")
        score_events = min(score_events + 0.3, 3.0)

    # 研报催化（近期研报密集代表机构关注度提升）
    if len(research_reports) >= 5:
        catalysts.append(f"近期研报密集（{len(research_reports)} 篇），机构调研催化潜力大")
        score_events = min(score_events + 0.5, 3.0)
    elif len(research_reports) >= 3:
        catalysts.append(f"近期研报 {len(research_reports)} 篇，有一定机构关注")
        score_events = min(score_events + 0.3, 3.0)

    # 龙虎榜（近期上榜代表资金关注）
    if dragon_tiger:
        catalysts.append("近期上龙虎榜，资金关注度大幅提升")
        score_events = min(score_events + 0.3, 3.0)

    if catalysts:
        findings.extend(catalysts[:3])
    else:
        findings.append("近期暂无明显催化事件窗口，等待公告或行业政策推动")

    # ── 预期差空间（4分）──
    score_expectation = 2.0
    expectation_items: list[str] = []
    if profit_yoy is not None:
        if profit_yoy > 50:
            score_expectation = 4.0
            expectation_items.append(f"净利润同比 +{profit_yoy:.1f}%，业绩高速增长，超预期弹性大")
        elif profit_yoy > 20:
            score_expectation = 3.5
            expectation_items.append(f"净利润同比 +{profit_yoy:.1f}%，业绩稳健增长，超预期概率中等")
        elif profit_yoy > 0:
            score_expectation = 2.5
            expectation_items.append(f"净利润同比 +{profit_yoy:.1f}%，业绩温和增长")
        elif profit_yoy > -20:
            score_expectation = 1.5
            expectation_items.append(f"净利润同比 {profit_yoy:.1f}%，业绩承压，超预期难度大")
        else:
            score_expectation = 1.0
            expectation_items.append(f"⚠️ 净利润同比 {profit_yoy:.1f}%，业绩大幅下滑，不及预期风险高")
    if expectation_items:
        findings.extend(expectation_items[:2])

    # ── 落地确定性（3分）──
    score_certainty = 1.5
    risk_events: list[str] = []
    # 质押风险
    if pledge_ratio is not None and pledge_ratio > 30:
        risk_events.append(f"⚠️ 质押比例 {pledge_ratio:.1f}%（>30%），解禁/质押爆仓风险")
        score_certainty = max(score_certainty - 0.5, 0.5)
    # 业绩确定性
    if revenue_yoy is not None and profit_yoy is not None:
        if revenue_yoy > 0 and profit_yoy > 0:
            score_certainty = min(score_certainty + 0.5, 3.0)
            findings.append("营收+利润双增，业绩催化落地确定性高")
        elif revenue_yoy > 0 and profit_yoy <= 0:
            findings.append("⚠️ 营收增长但利润下滑，成本压力侵蚀业绩确定性")
    # 近期无负面信号时提升确定性
    if not risk_events and len(research_reports) >= 3:
        score_certainty = min(score_certainty + 0.3, 3.0)
    if risk_events:
        findings.extend(risk_events[:2])

    total = score_events + score_expectation + score_certainty
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M12",
        module_name="催化事件与前瞻预期",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice="短线：提前布局业绩预告/研报发布催化，兑现后止盈",
        mid_advice=f"中线：当前处于{month}月，{'业绩窗口期，可持仓等待' if month in [1,2,3,4,7,8,10] else '非业绩窗口，依靠行业政策驱动'}",
        long_advice="长线：只有基本面持续改善的催化才构成长线买入依据，事件性催化不宜重仓",
        conclusion=f"催化预期评分 {total:.1f}/10，近期催化窗口 {len(catalysts)} 个，业绩增速 {'N/A' if profit_yoy is None else f'+{profit_yoy:.1f}%'}",
        detail={
            "catalysts": catalysts,
            "profit_yoy": profit_yoy,
            "pledge_ratio": pledge_ratio,
            "research_count": len(research_reports),
        },
    )
