"""M02 财务质量深度核验"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt, pct_fmt, yi


def analyze_financial(data: dict) -> ModuleResult:
    fi = data.get("financial_indicator") or {}
    profits = data.get("profit_statement") or []
    bs = data.get("balance_sheet") or {}
    cf = data.get("cashflow") or {}
    annual = data.get("annual_financial") or []

    findings = []
    warnings = []
    score = 5.0

    # ── 盈利能力 ──
    roe = fi.get("roe")
    gross_margin = fi.get("gross_margin")
    net_margin = fi.get("net_margin")

    if roe is not None:
        findings.append(f"ROE：{fmt(roe)}%")
        if roe >= 20:
            score += 2.0
            findings.append("✅ ROE > 20%，高盈利能力，具备核心竞争力")
        elif roe >= 15:
            score += 1.5
            findings.append("✅ ROE > 15%，良好盈利能力")
        elif roe >= 10:
            score += 0.5
        elif roe < 5:
            score -= 1.0
            warnings.append("⚠️ ROE < 5%，盈利能力偏弱")

    if gross_margin is not None:
        findings.append(f"毛利率：{fmt(gross_margin)}%，净利率：{fmt(net_margin) if net_margin is not None else 'N/A'}%")
        if gross_margin >= 40:
            score += 1.0
            findings.append("✅ 毛利率 > 40%，高毛利行业护城河显著")
        elif gross_margin < 10:
            warnings.append("⚠️ 毛利率 < 10%，产品竞争同质化严重")
    else:
        findings.append("ℹ️ 毛利率数据暂缺（可能因行业分类不同或API限制）")

    # ── 近3年年度财务趋势 ──
    if annual:
        findings.append("--- 近年度营收与利润趋势 ---")
        for yr in annual[:4]:
            year = yr.get("year", "")
            rev = yr.get("revenue")
            np_ = yr.get("net_profit")
            gm = yr.get("gross_margin")
            rd = yr.get("rd_expense")
            rev_yoy = yr.get("revenue_yoy")
            pnl_yoy = yr.get("profit_yoy")
            line = f"{year}年：营收 {yi(rev)}，净利润 {yi(np_)}"
            if gm is not None:
                line += f"，毛利率 {fmt(gm)}%"
            if rd is not None:
                line += f"，研发 {yi(rd)}"
            if rev_yoy is not None:
                line += f"（营收同比 {pct_fmt(rev_yoy)}，利润同比 {pct_fmt(pnl_yoy)}）"
            findings.append(line)
        # 趋势判断：近2年净利润是否增长
        if len(annual) >= 2:
            np0 = annual[0].get("net_profit")
            np1 = annual[1].get("net_profit")
            if np0 and np1 and np1 != 0:
                trend_pct = (np0 - np1) / abs(np1) * 100
                if trend_pct >= 20:
                    score += 0.5
                    findings.append(f"✅ 年度净利润连续增长（最近一年 {pct_fmt(trend_pct)}），成长势头良好")
                elif trend_pct <= -20:
                    score -= 0.5
                    warnings.append(f"⚠️ 年度净利润同比下滑 {abs(trend_pct):.1f}%，需关注业绩持续性")

    # ── 成长性（最新季度利润表） ──
    if profits:
        latest = profits[0]
        revenue = latest.get("revenue")
        net_profit = latest.get("net_profit")
        rev_yoy = latest.get("revenue_yoy")
        pnl_yoy = latest.get("profit_yoy")
        rd_expense = latest.get("rd_expense")
        period = latest.get("period", "")

        if revenue:
            findings.append(f"最新期 ({period[:10]}) 营收：{yi(revenue)}，净利润：{yi(net_profit)}")
        if rd_expense:
            rev_val = revenue or 1
            rd_ratio = rd_expense / rev_val * 100 if rev_val > 0 else None
            findings.append(f"研发投入：{yi(rd_expense)}" + (f"（占营收 {rd_ratio:.1f}%）" if rd_ratio else ""))
        if rev_yoy is not None:
            findings.append(f"营收同比：{pct_fmt(rev_yoy)}，净利同比：{pct_fmt(pnl_yoy)}")
            if pnl_yoy and pnl_yoy >= 30:
                score += 1.5
                findings.append("✅ 净利润高增长（+30%+），业绩景气")
            elif pnl_yoy and pnl_yoy >= 10:
                score += 0.5
            elif pnl_yoy and pnl_yoy < -20:
                score -= 1.5
                warnings.append("🚨 净利润大幅下滑（-20%+），业绩恶化风险")

        # 扣非含金量
        deducted = latest.get("deducted_profit")
        if net_profit and deducted and net_profit > 0:
            quality_ratio = deducted / net_profit
            findings.append(f"扣非净利润/净利润：{quality_ratio:.2%}")
            if quality_ratio < 0.7:
                score -= 1.0
                warnings.append("⚠️ 扣非含金量低，净利润存在非经常性收益虚增")
            elif quality_ratio >= 0.9:
                score += 0.5

    # ── 财务安全性 ──
    debt_ratio = fi.get("debt_ratio")
    if debt_ratio is not None:
        findings.append(f"资产负债率：{fmt(debt_ratio)}%")
        if debt_ratio > 70:
            score -= 1.5
            warnings.append(f"🚨 资产负债率 {debt_ratio:.1f}%，财务杠杆过高")
        elif debt_ratio > 60:
            score -= 0.5
            warnings.append(f"⚠️ 资产负债率 {debt_ratio:.1f}%，偏高需关注")
        elif debt_ratio < 40:
            score += 0.5
            findings.append("✅ 资产负债率健康，财务安全性强")

    # ── 现金流质量 ──
    op_cf = cf.get("operating_cf")
    net_p = profits[0].get("net_profit") if profits else None
    if op_cf and net_p and net_p > 0:
        cf_ratio = op_cf / net_p
        findings.append(f"经营现金流/净利润：{cf_ratio:.2f}x（数据来源：最新季报）")
        if cf_ratio >= 1.2:
            score += 1.0
            findings.append("✅ 现金流质量优秀，利润含金量高")
        elif cf_ratio < 0.5:
            score -= 1.0
            warnings.append("⚠️ 现金流与净利润严重背离，盈利质量存疑")

    # ── 资产负债表风险排查 ──
    goodwill = bs.get("goodwill")
    total_assets = bs.get("total_assets")
    if goodwill and total_assets and total_assets > 0:
        goodwill_ratio = goodwill / total_assets
        if goodwill_ratio > 0.3:
            score -= 1.0
            warnings.append(f"🚨 商誉占总资产 {goodwill_ratio:.1%}，减值风险高")
        elif goodwill_ratio > 0.15:
            warnings.append(f"⚠️ 商誉占比 {goodwill_ratio:.1%}，需关注减值风险")

    # 存贷双高检查
    cash = bs.get("cash")
    interest_debt = bs.get("interest_bearing_debt")
    if cash and interest_debt and cash > 0 and interest_debt > 0:
        if interest_debt / cash > 2:
            warnings.append("⚠️ 疑似存贷双高异常：大量有息负债同时持有大量现金")

    score = min(10.0, max(1.0, score))

    # 类型判断
    if score >= 8:
        fin_type = "真成长"
    elif score >= 7:
        fin_type = "稳健盈利"
    elif score >= 5:
        fin_type = "普通质量"
    elif score >= 3:
        fin_type = "财务隐患"
    else:
        fin_type = "业绩拐点/财务风险"

    all_findings = findings + warnings
    conclusion = f"财务质量评级：{fin_type}。{warnings[0] if warnings else '整体财务健康，无重大风险信号。'}"

    return ModuleResult(
        module_id="M02",
        module_name="财务质量深度核验",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice="关注最新季报业绩数据，有无超预期或不及预期",
        mid_advice="跟踪ROE与现金流趋势，持续改善则中线可持有",
        long_advice="ROE持续>15%且现金流健康的标的具备长线价值投资属性",
        conclusion=conclusion,
        detail={"financial_indicator": fi, "balance_sheet": bs, "cashflow": cf},
    )
