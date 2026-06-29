"""M02 — 财务质量深度核验（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str


def analyze_financial(data: dict) -> ModuleResult:
    roe = safe_float(data.get("roe"))
    gross_margin = safe_float(data.get("gross_margin"))
    net_margin = safe_float(data.get("net_margin"))
    revenue_yoy = safe_float(data.get("revenue_yoy"))
    profit_yoy = safe_float(data.get("profit_yoy"))
    debt_ratio = safe_float(data.get("debt_ratio"))
    goodwill_ratio = safe_float(data.get("goodwill_ratio"))
    ocf = safe_float(data.get("ocf"))
    net_profit = safe_float(data.get("net_profit"))
    profit_deducted = safe_float(data.get("profit_deducted"))
    three_fee_ratio = safe_float(data.get("three_fee_ratio"))
    rd_expense = safe_float(data.get("rd_expense"))
    annual_history = data.get("annual_history") or []
    cash = safe_float(data.get("cash"))
    accounts_receivable = safe_float(data.get("accounts_receivable"))

    findings: list[str] = []

    # ── 盈利成长性（2分）──
    score_growth = 1.0
    if revenue_yoy is not None and profit_yoy is not None:
        if revenue_yoy > 20 and profit_yoy > 20:
            score_growth = 2.0
            findings.append(f"高速成长：营收同比 {pct_str(revenue_yoy)}，净利润同比 {pct_str(profit_yoy)}")
        elif revenue_yoy > 10 and profit_yoy > 10:
            score_growth = 1.7
            findings.append(f"稳健成长：营收同比 {pct_str(revenue_yoy)}，净利润同比 {pct_str(profit_yoy)}")
        elif revenue_yoy > 0 and profit_yoy > 0:
            score_growth = 1.4
            findings.append(f"温和成长：营收同比 {pct_str(revenue_yoy)}，净利润同比 {pct_str(profit_yoy)}")
        elif profit_yoy < -20:
            score_growth = 0.5
            findings.append(f"⚠️ 业绩大幅下滑：净利润同比 {pct_str(profit_yoy)}，需排查原因")
        else:
            score_growth = 1.0
            findings.append(f"业绩承压：营收同比 {pct_str(revenue_yoy)}，净利润同比 {pct_str(profit_yoy)}")
    else:
        findings.append("⚠️ 营收/净利润同比数据获取失败")

    # ── 盈利质量（2分）──
    score_quality = 1.0
    quality_items: list[str] = []
    if roe is not None:
        if roe > 20:
            score_quality += 0.5
            quality_items.append(f"ROE {pct_str(roe)}（优秀）")
        elif roe > 15:
            score_quality += 0.3
            quality_items.append(f"ROE {pct_str(roe)}（良好）")
        elif roe < 5:
            score_quality -= 0.3
            quality_items.append(f"ROE {pct_str(roe)}（偏低，盈利能力弱）")
        else:
            quality_items.append(f"ROE {pct_str(roe)}")
    if gross_margin is not None:
        quality_items.append(f"毛利率 {pct_str(gross_margin)}")
        if gross_margin > 50:
            score_quality += 0.3
    if net_margin is not None:
        quality_items.append(f"净利率 {pct_str(net_margin)}")
    if profit_deducted is not None and net_profit is not None and net_profit != 0:
        deducted_ratio = profit_deducted / net_profit
        if deducted_ratio < 0.8:
            score_quality -= 0.3
            quality_items.append(f"⚠️ 扣非/净利润比值 {deducted_ratio:.2f}，非经常性损益占比高，盈利含金量存疑")
        else:
            quality_items.append(f"扣非利润成色良好（比值 {deducted_ratio:.2f}）")
    if quality_items:
        findings.append("盈利质量：" + "，".join(quality_items))
    score_quality = round(max(0.5, min(2.0, score_quality)), 2)

    # ── 现金流健康度（2分）──
    score_cf = 1.0
    if ocf is not None and net_profit is not None and net_profit != 0:
        cf_ratio = ocf / net_profit
        if cf_ratio > 1.2:
            score_cf = 2.0
            findings.append(f"现金流优质：经营现金流/净利润 = {cf_ratio:.2f}（超过1.2，利润真实性高）")
        elif cf_ratio > 0.8:
            score_cf = 1.6
            findings.append(f"现金流良好：经营现金流/净利润 = {cf_ratio:.2f}")
        elif cf_ratio < 0:
            score_cf = 0.5
            findings.append(f"⚠️ 经营现金流为负（{ocf:.1f}亿），利润质量存疑，需重点排查")
        else:
            score_cf = 1.0
            findings.append(f"现金流偏弱：经营现金流/净利润 = {cf_ratio:.2f}")
    elif ocf is not None:
        if ocf > 0:
            score_cf = 1.5
            findings.append(f"经营现金流为正（{ocf:.1f}亿）")
        else:
            score_cf = 0.5
            findings.append(f"⚠️ 经营现金流为负（{ocf:.1f}亿）")
    else:
        findings.append("⚠️ 现金流数据获取失败")

    # ── 财务安全性（2分）──
    score_safety = 1.5
    safety_items: list[str] = []
    if debt_ratio is not None:
        safety_items.append(f"资产负债率 {pct_str(debt_ratio)}")
        if debt_ratio > 70:
            score_safety -= 0.5
            safety_items[-1] += "（⚠️ 偏高，偿债压力大）"
        elif debt_ratio < 40:
            score_safety += 0.3
            safety_items[-1] += "（健康）"
    if goodwill_ratio is not None and goodwill_ratio > 15:
        score_safety -= 0.3
        safety_items.append(f"⚠️ 商誉占总资产 {pct_str(goodwill_ratio)}，减值风险较高")
    if cash is not None and accounts_receivable is not None and accounts_receivable > 0:
        storage_cash_ratio = cash / accounts_receivable if accounts_receivable > 0 else 999
        if storage_cash_ratio < 0.5:
            score_safety -= 0.2
            safety_items.append("⚠️ 货币资金/应收账款比值偏低，关注资金链风险")
    if safety_items:
        findings.append("财务安全：" + "，".join(safety_items))
    score_safety = round(max(0.5, min(2.0, score_safety)), 2)

    # ── 股东回报（2分）──
    score_dividend = 1.5
    dividend_yield = safe_float(data.get("dividend_yield"))
    if dividend_yield is not None:
        if dividend_yield > 4:
            score_dividend = 2.0
            findings.append(f"高股息标的：股息率 {pct_str(dividend_yield)}，股东回报优秀")
        elif dividend_yield > 2:
            score_dividend = 1.8
            findings.append(f"股息率 {pct_str(dividend_yield)}，股东回报良好")
        else:
            score_dividend = 1.5
            findings.append(f"股息率 {pct_str(dividend_yield)}，回报一般")
    else:
        findings.append("股息率数据暂缺，股东回报评估依赖年报分红记录")

    # 三费率检查
    if three_fee_ratio is not None:
        if three_fee_ratio > 30:
            findings.append(f"⚠️ 三费占收入比 {pct_str(three_fee_ratio)}，费用管控能力偏弱")
        else:
            findings.append(f"三费率 {pct_str(three_fee_ratio)}，费用管控合理")

    total = score_growth + score_quality + score_cf + score_safety + score_dividend
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    label_map = {5: "真成长", 4: "稳健盈利", 3: "普通标的", 2: "业绩承压", 1: "财务隐患"}
    label = label_map.get(stars, "待定")

    return ModuleResult(
        module_id="M02",
        module_name="财务质量深度核验",
        score=total,
        stars=stars,
        key_findings=findings[:6],
        short_advice="短线：关注季报超预期可能性，确认扣非利润含金量",
        mid_advice=f"中线：跟踪现金流转正趋势，{'ROE若持续>15%可加仓' if roe and roe > 15 else '警惕利润质量恶化风险'}",
        long_advice="长线：ROE+现金流双优是核心持仓标准，负债率>70%须谨慎",
        conclusion=f"财务质量评级：【{label}】，综合评分 {total:.1f}/10，ROE {pct_str(roe)}，毛利率 {pct_str(gross_margin)}",
        detail={
            "roe": roe, "gross_margin": gross_margin, "net_margin": net_margin,
            "revenue_yoy": revenue_yoy, "profit_yoy": profit_yoy,
            "debt_ratio": debt_ratio, "ocf": ocf,
        },
    )
