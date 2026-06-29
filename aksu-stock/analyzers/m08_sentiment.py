"""M08 — 题材情绪与市场热度分析（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str


def analyze_sentiment(data: dict) -> ModuleResult:
    pct_change = safe_float(data.get("pct_change"))
    turnover_rate = safe_float(data.get("turnover_rate"))
    market_sentiment = data.get("market_sentiment") or {}
    research_reports = data.get("research_reports") or []
    concepts = data.get("stock_concepts") or []
    dragon_tiger = data.get("dragon_tiger") or []
    industry = data.get("industry") or "未知行业"
    market_cap = safe_float(data.get("market_cap"))

    findings: list[str] = []

    # ── 题材硬核度（3分）──
    score_theme = 1.5
    hot_keywords = [
        "人工智能", "AI", "芯片", "半导体", "新能源", "储能", "光伏", "军工", "国产替代",
        "机器人", "医药", "生物", "大模型", "数据", "算力", "量子", "低空", "卫星",
    ]
    hit_keywords = [kw for kw in hot_keywords if any(kw in c for c in concepts) or kw in industry]
    if hit_keywords:
        score_theme = 3.0 if len(hit_keywords) >= 3 else 2.5 if len(hit_keywords) >= 2 else 2.0
        findings.append(f"题材热度：命中主流热点 {len(hit_keywords)} 个（{', '.join(hit_keywords[:3])}），题材硬核度高")
    else:
        findings.append(f"所属行业【{industry}】，暂无明显热门题材标签，题材硬核度一般")

    if concepts:
        findings.append(f"概念标签：{', '.join(concepts[:5])}{'等' if len(concepts) > 5 else ''}")

    # ── 概念稀缺性（3分）──
    score_scarcity = 1.5
    if market_cap is not None:
        if market_cap < 1e10:
            score_scarcity = 3.0
            findings.append("市值偏小（<100亿），题材炒作弹性高，概念稀缺性强")
        elif market_cap < 5e10:
            score_scarcity = 2.5
            findings.append(f"中小市值（{market_cap/1e8:.0f}亿），题材炒作空间适中")
        elif market_cap < 2e11:
            score_scarcity = 2.0
            findings.append(f"中等市值（{market_cap/1e8:.0f}亿），需要更强题材支撑")
        else:
            score_scarcity = 1.5
            findings.append(f"大市值（{market_cap/1e8:.0f}亿），题材炒作弹性有限，稳健持仓为主")

    # ── 情绪溢价空间（4分）──
    score_emotion = 2.0
    emotion_items: list[str] = []
    # 全市场情绪
    limit_up = safe_float(market_sentiment.get("limit_up_count"))
    limit_down = safe_float(market_sentiment.get("limit_down_count"))
    if limit_up is not None and limit_down is not None:
        market_heat = limit_up / max(limit_down + 1, 1)
        if market_heat > 5:
            score_emotion = 4.0
            emotion_items.append(f"全市场情绪亢奋：涨停 {int(limit_up)} / 跌停 {int(limit_down)}，赚钱效应极强")
        elif market_heat > 2:
            score_emotion = 3.0
            emotion_items.append(f"全市场情绪乐观：涨停 {int(limit_up)} / 跌停 {int(limit_down)}")
        elif market_heat > 0.5:
            score_emotion = 2.0
            emotion_items.append(f"全市场情绪中性：涨停 {int(limit_up)} / 跌停 {int(limit_down)}")
        else:
            score_emotion = 1.0
            emotion_items.append(f"⚠️ 全市场情绪悲观：涨停 {int(limit_up)} / 跌停 {int(limit_down)}")

    # 个股今日表现
    if pct_change is not None:
        if pct_change >= 9.5:
            emotion_items.append(f"今日涨停（+{pct_str(pct_change)}），情绪溢价顶格")
        elif pct_change >= 5:
            emotion_items.append(f"今日大涨 {pct_str(pct_change)}，个股情绪高亢")
        elif pct_change <= -9.5:
            emotion_items.append(f"今日跌停（{pct_str(pct_change)}），情绪极度悲观")
        elif pct_change <= -3:
            emotion_items.append(f"今日下跌 {pct_str(pct_change)}，情绪偏弱")

    if dragon_tiger:
        emotion_items.append(f"进入龙虎榜，市场关注度大幅提升，情绪催化作用明显")
        score_emotion = min(score_emotion + 0.5, 4.0)

    findings.extend(emotion_items[:3])

    if turnover_rate is not None:
        if turnover_rate > 10:
            findings.append(f"换手率 {pct_str(turnover_rate)}，交投活跃，情绪炒作特征明显")
        elif turnover_rate > 5:
            findings.append(f"换手率 {pct_str(turnover_rate)}，成交适中")

    total = score_theme + score_scarcity + score_emotion
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M08",
        module_name="题材情绪与市场热度",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice=f"短线：{'情绪高温，适合追涨做T' if score_emotion >= 3 else '情绪中性，等待板块启动再介入' if score_emotion >= 2 else '情绪低迷，避免逆势操作'}",
        mid_advice=f"中线：题材硬核度{'高，可持续炒作' if score_theme >= 2.5 else '一般，注意退潮风险'}",
        long_advice="长线：题材属性标的不宜做长线，若业绩无法支撑，回归基本面后估值大幅重估",
        conclusion=f"题材情绪评分 {total:.1f}/10，题材热度【{'极高' if score_theme >= 2.5 else '中等' if score_theme >= 2 else '一般'}】，市场情绪【{'亢奋' if score_emotion >= 3.5 else '乐观' if score_emotion >= 2.5 else '中性' if score_emotion >= 1.5 else '悲观'}】",
        detail={
            "hit_keywords": hit_keywords,
            "market_cap": market_cap,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "pct_change": pct_change,
        },
    )
