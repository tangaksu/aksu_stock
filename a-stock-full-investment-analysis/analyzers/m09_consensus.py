"""M09 市场分歧与机构预期统计"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt


def analyze_consensus(data: dict) -> ModuleResult:
    reports = data.get("research_reports") or []
    consensus = data.get("analyst_consensus") or {}
    rt = data.get("realtime") or {}

    findings = []
    score = 5.0

    # ── 机构评级统计 ──
    buy = consensus.get("buy", 0)
    hold = consensus.get("hold", 0)
    sell = consensus.get("sell", 0)
    total = consensus.get("total", 0)
    buy_ratio = consensus.get("buy_ratio", 0)
    avg_target = consensus.get("avg_target")
    max_target = consensus.get("max_target")
    min_target = consensus.get("min_target")

    # 若机构一致预期API数据为空，从研报列表派生
    if total == 0 and reports:
        for r in reports:
            rating = r.get("rating", "")
            if "买入" in rating or "增持" in rating or "推荐" in rating or "强推" in rating:
                buy += 1
            elif "中性" in rating or "持有" in rating or "观望" in rating:
                hold += 1
            elif "减持" in rating or "卖出" in rating:
                sell += 1
        total = buy + hold + sell
        if total > 0:
            buy_ratio = round(buy / total * 100, 1)
        # 目标价从研报派生
        target_prices = [r.get("target_price") for r in reports if r.get("target_price")]
        if target_prices:
            avg_target = round(sum(target_prices) / len(target_prices), 2)
            max_target = round(max(target_prices), 2)
            min_target = round(min(target_prices), 2)
        findings.append(f"ℹ️ 一致预期来源：研报评级汇总（机构预测API暂缺，从 {len(reports)} 篇研报提取）")

    if total > 0:
        findings.append(
            f"机构评级（近6个月）：买入/增持 {buy}家，中性 {hold}家，减持/卖出 {sell}家（共 {total} 家）"
        )
        findings.append(f"买入评级占比：{buy_ratio:.1f}%（数据来源：机构研报评级汇总）")

        if buy_ratio >= 80:
            score += 2.0
            findings.append("✅ 机构高度看多（买入占比>80%），强共识")
        elif buy_ratio >= 60:
            score += 1.0
            findings.append("✅ 机构多数看多（买入占比>60%）")
        elif buy_ratio < 30:
            score -= 1.5
            findings.append("⚠️ 机构看空居多，市场信心不足")

        if sell > 0:
            findings.append(f"⚠️ 有 {sell} 家机构给出减持/卖出评级，注意分歧")
    else:
        findings.append("ℹ️ 暂未获取到机构评级数据（该股机构覆盖可能较少）")

    # ── 目标价分析（预期差） ──
    current_price = rt.get("price")
    if avg_target and current_price and current_price > 0:
        upside = (avg_target - current_price) / current_price * 100
        findings.append(
            f"机构目标价：均值 {fmt(avg_target)}（上行空间 {upside:+.1f}%），"
            f"区间 {fmt(min_target)} ~ {fmt(max_target)}（数据来源：研报目标价）"
        )
        if upside >= 30:
            score += 2.0
            findings.append("✅ 机构目标价上行空间 > 30%，预期差显著")
        elif upside >= 15:
            score += 1.0
            findings.append("✅ 机构目标价上行空间 > 15%，有一定预期差")
        elif upside < 0:
            score -= 1.5
            findings.append(f"⚠️ 当前价格已超机构目标价（下行空间 {abs(upside):.1f}%），高估警示")
        elif upside < 5:
            findings.append(f"ℹ️ 机构目标价上行空间不足 5%，安全边际有限")

    # ── 研报分析 ──
    if reports:
        findings.append(f"近期研报：共 {len(reports)} 篇，覆盖机构如下：")
        # 展示机构名称与评级（去重）
        seen = set()
        for r in reports[:6]:
            institution = r.get("institution", "")
            title = r.get("title", "")[:25]
            rating = r.get("rating", "")
            tp = r.get("target_price")
            date = r.get("date", "")[:10]
            key = f"{institution}-{rating}"
            if key not in seen:
                seen.add(key)
                tp_str = f"，目标价 {fmt(tp)}" if tp else ""
                findings.append(f"  [{date}] {institution}《{title}》评级：{rating}{tp_str}")
        if len(reports) >= 5:
            score += 0.5
            findings.append("✅ 研报覆盖度高（近期≥5篇），机构持续关注")
        # 研报密集度
        recent_ratings = [r.get("rating", "") for r in reports[:5]]
        buy_ratings = [r for r in recent_ratings if any(k in r for k in ("买入", "增持", "推荐", "强推"))]
        if len(buy_ratings) >= 3:
            score += 0.5
            findings.append("✅ 近5篇研报中多数评级看多，机构共识强")
    else:
        score -= 0.5
        findings.append("⚠️ 机构研报稀缺，关注度不足，信息透明度低")

    score = min(10.0, max(1.0, score))

    conclusion = (
        f"机构覆盖 {total} 家，买入评级占 {buy_ratio:.0f}%。"
        + (f"平均目标价 {fmt(avg_target)}，上行空间约 {(avg_target - current_price) / current_price * 100:.1f}%。"
           if avg_target and current_price else "")
    )

    return ModuleResult(
        module_id="M09",
        module_name="市场分歧与机构预期统计",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice="关注研报超预期发布或评级上调，短线催化效应明显",
        mid_advice=f"{'机构共识做多，中线持有有支撑' if buy_ratio >= 60 else '机构分歧较大，中线需跟踪业绩兑现'}",
        long_advice=f"目标价空间{'充裕，长线价值显现' if avg_target and current_price and (avg_target - current_price) / current_price > 0.2 else '有限，长线需关注估值水平'}",
        conclusion=conclusion,
        detail={"consensus": consensus, "report_count": len(reports), "derived_buy": buy, "derived_total": total},
    )
