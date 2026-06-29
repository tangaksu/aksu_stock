"""M10 大盘联动与市场风格适配分析"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt, pct_fmt


def _calc_stock_volatility(stock_closes: list) -> float | None:
    """
    计算个股年化波动率（简化版相对强弱估算）。
    注：完整Beta计算需同期指数收益率数据，此处仅计算股票自身波动率
    作为独立性/弹性参考指标。
    """
    if not stock_closes or len(stock_closes) < 20:
        return None
    n = min(len(stock_closes), 60)
    s_ret = [(stock_closes[-n + i + 1] - stock_closes[-n + i]) / stock_closes[-n + i]
             for i in range(n - 1)]
    if not s_ret:
        return None
    avg = sum(s_ret) / len(s_ret)
    variance = sum((r - avg) ** 2 for r in s_ret) / len(s_ret)
    # 年化波动率（近似）
    return round(variance ** 0.5 * (250 ** 0.5) * 100, 2)


def analyze_market(data: dict) -> ModuleResult:
    index_data = data.get("index_data") or {}
    rt = data.get("realtime") or {}
    df = data.get("kline_df")
    info = data.get("stock_info") or {}

    findings = []
    score = 5.0

    # ── 主要指数行情 ──
    if index_data:
        for name, idx in index_data.items():
            pct = idx.get("pct_change")
            price = idx.get("price")
            if pct is not None:
                icon = "🔴" if pct > 0 else "🟢"
                findings.append(f"{icon} {name}：{price:.2f}（{pct:+.2f}%）")

        # 判断大盘整体方向
        all_pcts = [v.get("pct_change") or 0 for v in index_data.values()]
        avg_index_pct = sum(all_pcts) / len(all_pcts) if all_pcts else 0

        if avg_index_pct > 1.5:
            score += 1.5
            findings.append("✅ 大盘强势上涨，做多环境良好")
            market_style = "进攻市"
        elif avg_index_pct > 0:
            score += 0.5
            market_style = "温和多头"
        elif avg_index_pct < -2:
            score -= 2.0
            findings.append("🚨 大盘大幅下跌，系统性风险，建议减仓防御")
            market_style = "防御市"
        elif avg_index_pct < 0:
            score -= 0.5
            market_style = "弱势震荡"
        else:
            market_style = "平衡震荡"

    else:
        market_style = "数据不足"

    # ── 个股与大盘的相对强弱 ──
    stock_pct = rt.get("pct_change") or 0
    if index_data:
        sh_pct = (index_data.get("上证指数") or {}).get("pct_change") or 0
        relative = stock_pct - sh_pct
        findings.append(f"个股今日涨跌：{stock_pct:+.2f}%，上证：{sh_pct:+.2f}%，相对强弱：{relative:+.2f}%")

        if relative > 3:
            score += 1.5
            findings.append("✅ 个股大幅跑赢大盘，独立行情特征明显")
        elif relative > 1:
            score += 0.5
            findings.append("✅ 个股跑赢大盘，相对强势")
        elif relative < -3:
            score -= 1.5
            findings.append("⚠️ 个股大幅跑输大盘，弱势偏空")
        elif relative < -1:
            score -= 0.5
            findings.append("⚠️ 个股跑输大盘，相对弱势")

    # ── 市场风格判断与标的适配度 ──
    industry = info.get("industry", "")
    style_fit = "中性"

    if market_style in ("进攻市", "温和多头"):
        if any(k in industry for k in ["科技", "芯片", "AI", "成长", "新能源"]):
            style_fit = "高度适配"
            score += 1.0
            findings.append("✅ 进攻市环境 × 成长科技属性：风格高度匹配，弹性强")
        elif any(k in industry for k in ["白酒", "消费", "医药"]):
            style_fit = "中性适配"
            findings.append("ℹ️ 进攻市环境 × 消费防御属性：弹性较小，跟涨有限")

    elif market_style in ("防御市", "弱势震荡"):
        if any(k in industry for k in ["白酒", "公用事业", "医药", "消费"]):
            style_fit = "高度适配"
            score += 0.5
            findings.append("✅ 防御市环境 × 防御属性：相对抗跌，风格匹配")
        elif any(k in industry for k in ["钢铁", "煤炭", "化工", "周期"]):
            style_fit = "低适配"
            score -= 0.5
            findings.append("⚠️ 防御市环境 × 周期属性：风格错配，杀跌风险较高")

    score = min(10.0, max(1.0, score))

    conclusion = (
        f"当前大盘风格：{market_style}，个股风格适配度：{style_fit}。"
        f"{'风格匹配，可适当加大配置比例。' if style_fit == '高度适配' else '注意风格切换风险，控制仓位。'}"
    )

    return ModuleResult(
        module_id="M10",
        module_name="大盘联动与市场风格适配分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice=f"大盘{market_style}环境下，{'短线积极做多' if score >= 6 else '短线以防御为主'}",
        mid_advice=f"中线关注大盘风格切换信号，{style_fit}标的优先配置",
        long_advice="长线穿越牛熊，聚焦基本面，弱化大盘短期影响",
        conclusion=conclusion,
        detail={"market_style": market_style, "style_fit": style_fit, "index_data": index_data},
    )
