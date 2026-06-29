"""M08 题材情绪与市场热度分析"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars


def analyze_sentiment(data: dict) -> ModuleResult:
    info = data.get("stock_info") or {}
    sentiment = data.get("market_sentiment") or {}
    rt = data.get("realtime") or {}

    findings = []
    score = 5.0

    industry = info.get("industry", "")
    board = info.get("board", "")

    # ── 大盘情绪 ──
    up_count = sentiment.get("up_count")
    down_count = sentiment.get("down_count")
    limit_up = sentiment.get("limit_up")
    limit_down = sentiment.get("limit_down")
    mood = sentiment.get("mood_score")

    if mood is not None:
        findings.append(
            f"市场情绪：涨{up_count}跌{down_count}，"
            f"涨停{limit_up}家/跌停{limit_down}家，"
            f"情绪温度：{mood:.0f}%"
        )
        if mood >= 65:
            score += 1.5
            findings.append("✅ 市场整体偏多，赚钱效应强，做多窗口期")
        elif mood >= 55:
            score += 0.5
            findings.append("✅ 市场温和偏多，中性略强")
        elif mood <= 35:
            score -= 1.5
            findings.append("⚠️ 市场情绪极度悲观，全面杀跌行情，谨慎持仓")
        elif mood <= 45:
            score -= 0.5
            findings.append("⚠️ 市场偏弱，赚钱效应差")

    # 涨停与跌停比判断情绪强弱
    if limit_up and limit_down:
        if limit_up > limit_down * 3:
            score += 0.5
            findings.append("✅ 涨停大于跌停3倍以上，情绪偏强")
        elif limit_down > limit_up * 2:
            score -= 1.0
            findings.append("⚠️ 跌停家数倍于涨停，情绪恶化信号")

    # ── 题材热度判断 ──
    hot_themes = {
        "AI": "人工智能", "芯片": "半导体芯片", "新能源": "新能源汽车",
        "光伏": "光伏储能", "机器人": "人形机器人", "低空经济": "低空经济",
        "华为": "华为产业链", "苹果": "苹果产业链", "核电": "核能核电",
    }

    matched_themes = []
    for key, theme in hot_themes.items():
        if key in industry or key in board or key in info.get("name", "") or key in info.get("business", ""):
            matched_themes.append(theme)

    if matched_themes:
        score += min(2.0, len(matched_themes) * 0.7)
        findings.append(f"✅ 匹配热门题材：{'、'.join(matched_themes)}")
    else:
        findings.append("ℹ️ 未匹配当前主流热门题材，题材溢价空间有限")

    # ── 个股当日情绪 ──
    pct = rt.get("pct_change") or 0
    turnover = rt.get("turnover_rate")

    if turnover:
        findings.append(f"换手率：{turnover:.2f}%")
        if turnover > 10:
            score += 1.0
            findings.append("✅ 换手率 > 10%，资金活跃，市场关注度高")
        elif turnover > 5:
            score += 0.3
        elif turnover < 1:
            findings.append("⚠️ 换手极低，市场关注度不足，流动性风险")

    if abs(pct) >= 9.9:
        if pct > 0:
            findings.append("✅ 今日涨停，情绪最高点")
        else:
            findings.append("🚨 今日跌停，情绪最低点，慎接刀")
    elif pct > 5:
        findings.append(f"✅ 今日大涨 {pct:+.2f}%，强势表现")
    elif pct < -5:
        findings.append(f"⚠️ 今日大跌 {pct:+.2f}%，情绪受损")

    score = min(10.0, max(1.0, score))

    theme_str = "、".join(matched_themes) if matched_themes else "无明显热门题材"
    conclusion = f"题材属性：{theme_str}。市场情绪温度：{mood:.0f}%" if mood else f"题材属性：{theme_str}"

    return ModuleResult(
        module_id="M08",
        module_name="题材情绪与市场热度分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice="情绪强时跟随热点做弹性，情绪弱时减仓防御",
        mid_advice=f"{'题材具有持续性，中线可布局' if matched_themes else '题材稀缺性不强，中线依靠基本面'}",
        long_advice="情绪类投资应设置严格止盈位，不做长线持有",
        conclusion=conclusion,
        detail={"themes": matched_themes, "mood_score": mood, "pct": pct, "turnover": turnover},
    )
