"""M14 交易纪律与风控体系"""
from __future__ import annotations
import math
from .base import ModuleResult, score_to_stars, fmt


def analyze_risk_control(data: dict, module_results: dict | None = None) -> ModuleResult:
    rt = data.get("realtime") or {}
    df = data.get("kline_df")

    findings = []
    warnings = []
    score = 6.0  # 风控模块默认给中性分，以实际风险点扣分

    current = rt.get("price")
    pct = rt.get("pct_change") or 0

    # ── 关键价位计算 ──
    ma5 = ma10 = ma20 = ma30 = None
    max_drawdown = None
    annualized_vol = None
    closes = []

    if df is not None and not df.empty:
        close_col = "收盘" if "收盘" in df.columns else "close"
        closes = df[close_col].tolist()
        n = len(closes)

        def _ma(period):
            if n < period:
                return None
            return round(sum(closes[-period:]) / period, 2)

        ma5 = _ma(5)
        ma10 = _ma(10)
        ma20 = _ma(20)
        ma30 = _ma(30)

        # ── 最大回撤（近1年） ──
        if n >= 20:
            peak = closes[0]
            max_dd = 0.0
            for c in closes:
                if c > peak:
                    peak = c
                if peak > 0:
                    dd = (peak - c) / peak
                    if dd > max_dd:
                        max_dd = dd
            max_drawdown = round(max_dd * 100, 2)

        # ── 年化波动率（近250日日收益率标准差） ──
        if n >= 20:
            returns = []
            for i in range(1, min(n, 250)):
                if closes[i - 1] > 0:
                    returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
            if len(returns) >= 10:
                mean_r = sum(returns) / len(returns)
                variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
                daily_vol = math.sqrt(variance)
                annualized_vol = round(daily_vol * math.sqrt(252) * 100, 2)

    # ── 止损位体系 ──
    if current:
        stop_warn = ma10 or round(current * 0.95, 2)
        stop_risk = ma20 or round(current * 0.92, 2)
        stop_cut = round(current * 0.88, 2)

        findings.append(f"当前价格：{current:.2f}（今日涨跌：{pct:+.2f}%）")
        findings.append(f"🛡 预警止损位（减1/3）：{stop_warn:.2f}（MA10）")
        findings.append(f"🛡 风控止损位（再减1/3）：{stop_risk:.2f}（MA20）")
        findings.append(f"🛡 清仓止损位（全部）：{stop_cut:.2f}（-12%硬止损）")

        # 止盈位
        tp1 = round(current * 1.08, 2)
        tp2 = round(current * 1.15, 2)
        tp3 = round(current * 1.25, 2)
        findings.append(f"🎯 止盈位：+8%={tp1} | +15%={tp2} | +25%={tp3}")

        # 风险收益比（计算逻辑：止盈目标2(+15%) / 硬止损(-12%)）
        risk = current - stop_cut
        reward = tp2 - current
        if risk > 0:
            rr_ratio = round(reward / risk, 2)
            findings.append(
                f"📊 风险收益比（盈亏比）：{rr_ratio:.2f}:1"
                f"（计算依据：盈利目标{tp2}即+15% vs 止损{stop_cut:.2f}即-12%）"
            )
            if rr_ratio >= 2.0:
                score += 1.5
                findings.append("✅ 盈亏比 ≥ 2:1，满足开仓标准")
            elif rr_ratio >= 1.5:
                score += 0.5
                findings.append("✅ 盈亏比 ≥ 1.5:1，可以考虑小仓位")
            else:
                score -= 1.5
                warnings.append(f"⚠️ 盈亏比仅 {rr_ratio:.2f}:1，不满足风控标准（建议≥2:1）")

    # ── 量化风险指标 ──
    if max_drawdown is not None:
        findings.append(f"📉 近1年最大回撤：{max_drawdown:.2f}%（数据来源：复权日线K线）")
        if max_drawdown > 50:
            score -= 1.0
            warnings.append(f"🚨 近1年最大回撤超50%（{max_drawdown:.1f}%），极高波动风险")
        elif max_drawdown > 30:
            score -= 0.5
            warnings.append(f"⚠️ 近1年最大回撤 {max_drawdown:.1f}%，波动较大")
        else:
            findings.append(f"✅ 近1年最大回撤 {max_drawdown:.1f}%，回撤相对可控")

    if annualized_vol is not None:
        findings.append(f"📊 年化波动率：{annualized_vol:.2f}%（基于近{min(len(closes)-1, 249)}个交易日日收益率）")
        if annualized_vol > 60:
            score -= 0.5
            warnings.append(f"⚠️ 年化波动率 {annualized_vol:.1f}%，股价剧烈波动，投机属性强")
        elif annualized_vol > 40:
            findings.append(f"ℹ️ 年化波动率 {annualized_vol:.1f}%，波动率偏高，建议严格止损")
        else:
            findings.append(f"✅ 年化波动率 {annualized_vol:.1f}%，波动相对温和")

    # ── 情绪风控检测 ──
    if pct > 8:
        score -= 1.0
        warnings.append("⚠️ 情绪拦截：今日大涨接近涨停，追高风险极高，冲动追涨情绪需克制")
    elif pct < -8:
        warnings.append("⚠️ 情绪拦截：今日大跌接近跌停，恐慌割肉需克制，等待企稳信号")

    # ── 仓位建议 ──
    total_score = None
    if module_results:
        scores = [r.score for r in module_results.values() if hasattr(r, "score")]
        total_score = sum(scores) / len(scores) * 10 if scores else None

    if total_score:
        if total_score >= 75:
            position_advice = "可配置30-40%仓位"
        elif total_score >= 65:
            position_advice = "建议10-20%轻仓观察"
        elif total_score >= 55:
            position_advice = "建议5-10%试仓"
        else:
            position_advice = "不建议建仓，空仓观望"
        findings.append(f"📦 仓位建议：{position_advice}（基于各模块综合评分）")
    else:
        findings.append("📦 仓位建议：根据综合评分确定（评分≥75分配置30-40%，≥65分10-20%，<60分空仓）")

    # ── 杠杆警示 ──
    warnings.append("⛔ 杠杆门禁：任何情况下严禁借贷/融资进行高风险博弈操作")

    # ── 风险汇总 ──
    all_risks = [
        ("致命风险", ["股权质押爆仓", "财务造假", "退市风险"]),
        ("中度风险", ["业绩大幅下滑", "高位放量出货", "大股东持续减持"]),
        ("轻微风险", ["短期超买", "估值偏高", "解禁抛压"]),
    ]

    for level, risks in all_risks:
        findings.append(f"【{level}】需重点排查：{'、'.join(risks)}")

    score = min(10.0, max(1.0, score))
    all_findings = findings + warnings

    conclusion = (
        f"风控体系完整，止损三档设置明确。"
        f"{'风险收益比达标，可按计划入场。' if score >= 7 else '当前盈亏比偏低，建议等待更好的入场时机。'}"
        + (f"近1年最大回撤 {max_drawdown:.1f}%，年化波动率 {annualized_vol:.1f}%。" if max_drawdown and annualized_vol else "")
    )

    return ModuleResult(
        module_id="M14",
        module_name="交易纪律与风控体系",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice=f"严格执行止损纪律：预警{fmt(ma10)}→风控{fmt(ma20)}→清仓硬止损",
        mid_advice="分批建仓（1/3试仓→确认→加仓），每笔止损不超过总仓位2%",
        long_advice="长线仓位以基本面定期复核为主，季报发布后重新评估是否持仓",
        conclusion=conclusion,
        detail={
            "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma30": ma30,
            "max_drawdown": max_drawdown, "annualized_vol": annualized_vol,
        },
    )
