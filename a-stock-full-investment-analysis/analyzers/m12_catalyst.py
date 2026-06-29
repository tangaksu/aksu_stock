"""M12 催化事件与前瞻预期分析"""
from __future__ import annotations
from datetime import datetime
from .base import ModuleResult, score_to_stars


def analyze_catalyst(data: dict) -> ModuleResult:
    reports = data.get("research_reports") or []
    info = data.get("stock_info") or {}
    fi = data.get("financial_indicator") or {}
    profits = data.get("profit_statement") or []

    findings = []
    score = 5.0
    upcoming_catalysts = []
    upcoming_risks = []

    now = datetime.now()
    month = now.month

    industry = info.get("industry", "")

    # ── 季报/年报窗口判断 ──
    if month in (4, 8, 10, 1):
        findings.append(f"⏰ 当前处于财报披露窗口（{month}月），业绩报告即将/正在密集发布")
        score += 0.5
        upcoming_catalysts.append("业绩报告发布（含季报）")

    if profits:
        latest = profits[0]
        pnl_yoy = latest.get("profit_yoy")
        if pnl_yoy and pnl_yoy > 30:
            score += 1.5
            upcoming_catalysts.append(f"最新财报净利润同比+{pnl_yoy:.0f}%，业绩超预期催化")
            findings.append(f"✅ 最新业绩净利润同比+{pnl_yoy:.0f}%，正面催化明确")
        elif pnl_yoy and pnl_yoy < -20:
            score -= 1.0
            upcoming_risks.append(f"业绩大幅下滑（净利润同比{pnl_yoy:.0f}%），负面压制")
            findings.append(f"⚠️ 最新业绩净利润同比{pnl_yoy:.0f}%，存在业绩地雷风险")

    # ── 政策催化判断 ──
    policy_sensitive = {
        "新能源": "新能源补贴/碳中和政策",
        "芯片": "半导体国产化政策/大基金投资",
        "AI": "AI算力/大模型政策支持",
        "军工": "国防预算增加/武器采购",
        "医药": "医保目录调整/新药审批",
        "地产": "房地产救市政策",
        "消费": "促消费/内需扩张政策",
    }
    for key, policy_desc in policy_sensitive.items():
        if key in industry:
            score += 0.5
            upcoming_catalysts.append(f"潜在政策催化：{policy_desc}")
            findings.append(f"✅ {industry} 行业存在政策催化预期：{policy_desc}")
            break

    # ── 研报催化 ──
    if reports:
        from datetime import timedelta
        # 过去30天内发布的研报
        cutoff = (now - timedelta(days=30)).strftime("%Y-%m")
        recent_reports = [r for r in reports if r.get("date", "") >= cutoff]
        if recent_reports:
            score += 0.5
            upcoming_catalysts.append(f"近期{len(recent_reports)}篇新研报，机构持续关注")
            findings.append(f"✅ 近1个月新发研报 {len(recent_reports)} 篇，机构催化效应")

    # ── 解禁风险窗口 ──
    list_date = info.get("list_date", "")
    if list_date:
        try:
            ld = datetime.strptime(list_date[:10].replace("/", "-"), "%Y-%m-%d")
            months_listed = (now.year - ld.year) * 12 + (now.month - ld.month)
            if months_listed in range(6, 9):
                score -= 1.0
                upcoming_risks.append("次新股半年解禁期临近（约6-9个月），存在解禁抛压")
                findings.append("⚠️ 次新股解禁窗口临近，关注大股东减持公告")
            elif months_listed in range(12, 15):
                upcoming_risks.append("一年解禁锁定期临近，部分早期投资者可能减持")
                findings.append("⚠️ 上市约一年，关注首发股东解禁减持风险")
        except Exception:
            pass

    # ── 重要时间节点 ──
    if month in (3, 4):
        upcoming_catalysts.append("全国两会/政府工作报告（政策定调）")
    elif month == 12:
        upcoming_catalysts.append("中央经济工作会议（来年政策展望）")
    elif month in (7, 8):
        upcoming_catalysts.append("中报季业绩公告窗口")

    # 汇总催化与风险
    if upcoming_catalysts:
        findings.append(f"✅ 近1-3月催化事件：{' | '.join(upcoming_catalysts[:3])}")
        score += min(1.5, len(upcoming_catalysts) * 0.3)

    if upcoming_risks:
        findings.append(f"⚠️ 潜在风险窗口：{' | '.join(upcoming_risks[:2])}")
        score -= min(1.5, len(upcoming_risks) * 0.5)

    score = min(10.0, max(1.0, score))

    conclusion = (
        f"催化事件：{upcoming_catalysts[0] if upcoming_catalysts else '暂无明显催化'}。"
        f"主要风险：{upcoming_risks[0] if upcoming_risks else '无明确风险窗口'}。"
    )

    return ModuleResult(
        module_id="M12",
        module_name="催化事件与前瞻预期分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice="催化事件前1-2周布局，事件落地当日止盈，避免预期兑现后的高位套牢",
        mid_advice="重点跟踪业绩披露、政策落地两大催化核心，中线根据事件进展调整持仓",
        long_advice="解禁减持风险是长线潜在扰动因素，需提前关注减持公告",
        conclusion=conclusion,
        detail={"catalysts": upcoming_catalysts, "risks": upcoming_risks},
    )
