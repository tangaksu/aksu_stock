"""M11 量能换手与流动性专项分析"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt, yi


def analyze_liquidity(data: dict) -> ModuleResult:
    rt = data.get("realtime") or {}
    df = data.get("kline_df")

    findings = []
    warnings = []
    score = 5.0

    # ── 当日实时数据 ──
    amount = rt.get("amount", 0)  # 成交额（元）
    turnover = rt.get("turnover_rate")
    pct = rt.get("pct_change") or 0

    if amount:
        findings.append(f"今日成交额：{yi(amount)}")
        if amount < 1e7:  # < 1000万
            score -= 2.0
            warnings.append("🚨 成交额 < 1000万，流动性极差，闪崩风险高，严禁重仓")
        elif amount < 5e7:  # < 5000万
            score -= 1.0
            warnings.append("⚠️ 成交额 < 5000万，流动性偏低，大资金进出困难")
        elif amount > 5e9:  # > 50亿
            score += 1.5
            findings.append("✅ 成交额 > 50亿，流动性极佳，机构进出无障碍")
        elif amount > 5e8:  # > 5亿
            score += 0.5
            findings.append("✅ 成交额 > 5亿，流动性良好")

    if turnover is not None:
        findings.append(f"换手率：{turnover:.2f}%")
        if turnover < 0.5:
            score -= 1.0
            warnings.append("⚠️ 换手率 < 0.5%，成交萎缩，买卖力量枯竭")
        elif turnover > 20:
            findings.append("⚠️ 换手率 > 20%，交投极度活跃，可能短期情绪顶")
            score -= 0.3
        elif turnover > 5:
            score += 0.5
            findings.append("✅ 换手率活跃（5-20%），资金参与度高")

    # ── 历史量能分析（K线数据） ──
    if df is not None and not df.empty:
        vol_col = "成交量" if "成交量" in df.columns else "volume"
        close_col = "收盘" if "收盘" in df.columns else "close"

        if vol_col in df.columns:
            vols = df[vol_col].tolist()
            closes = df[close_col].tolist() if close_col in df.columns else []

            # 计算均量
            avg_vol5 = sum(vols[-5:]) / 5 if len(vols) >= 5 else None
            avg_vol10 = sum(vols[-10:]) / 10 if len(vols) >= 10 else None
            avg_vol20 = sum(vols[-20:]) / 20 if len(vols) >= 20 else None

            if avg_vol20:
                vol_ratio_5 = round(avg_vol5 / avg_vol20, 2) if avg_vol5 else None
                findings.append(
                    f"5日均量/20日均量：{vol_ratio_5:.2f}x"
                )
                if vol_ratio_5 and vol_ratio_5 > 2:
                    score += 1.0
                    findings.append("✅ 近5日放量显著（超20日均量2倍），资金积极介入")
                elif vol_ratio_5 and vol_ratio_5 < 0.5:
                    score -= 0.5
                    findings.append("⚠️ 近5日成交持续萎缩，市场关注度下降")

            # 量价背离检测
            if closes and len(closes) >= 10 and vols:
                recent_close_up = closes[-1] > closes[-10]
                recent_vol_down = vols[-1] < vols[-10]
                if recent_close_up and recent_vol_down:
                    score -= 0.5
                    findings.append("⚠️ 价涨量缩（近10日），上涨动能不足，注意头部风险")

            # 低位放量判断（底部确认信号）
            if closes:
                n60_low = min(closes[-60:]) if len(closes) >= 60 else min(closes)
                current = closes[-1]
                is_near_low = (current - n60_low) / n60_low < 0.15
                if is_near_low and avg_vol5 and avg_vol20 and avg_vol5 > avg_vol20 * 1.5:
                    score += 1.0
                    findings.append("✅ 低位放量（底部信号），筹码换手充分，反转可期")

    score = min(10.0, max(1.0, score))
    all_findings = findings + warnings

    # 流动性等级
    if score >= 8:
        liq_level = "优秀"
    elif score >= 6:
        liq_level = "良好"
    elif score >= 4:
        liq_level = "一般"
    else:
        liq_level = "偏差"

    conclusion = f"流动性评级：{liq_level}。成交额 {yi(amount)}，换手率 {fmt(turnover)}%。"

    return ModuleResult(
        module_id="M11",
        module_name="量能换手与流动性专项分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice=f"流动性{liq_level}，{'短线可灵活进出' if score >= 6 else '流动性不足，控制单次建仓量'}",
        mid_advice="量价配合良好（放量上涨）时中线加仓，量价背离（缩量上涨）时减仓",
        long_advice="选择日均成交额 > 1亿的标的以保证长线持仓可进出",
        conclusion=conclusion,
        detail={"amount": amount, "turnover": turnover, "liquidity_level": liq_level},
    )
