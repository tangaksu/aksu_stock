"""M10 — 大盘联动与市场风格适配（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_market(data: dict) -> ModuleResult:
    pct_change = safe_float(data.get("pct_change"))
    market_sentiment = data.get("market_sentiment") or {}
    north_net_inflow = safe_float((market_sentiment or {}).get("north_net_inflow_today"))
    limit_up = safe_float(market_sentiment.get("limit_up_count"))
    limit_down = safe_float(market_sentiment.get("limit_down_count"))
    market_cap = safe_float(data.get("market_cap"))
    pe_ttm = safe_float(data.get("pe_ttm"))
    roe = safe_float(data.get("roe"))
    kline_df = data.get("kline_df")

    findings: list[str] = []

    # ── 行情适配度（3分）──
    score_adapt = 1.5
    market_bull = False
    if limit_up is not None and limit_down is not None:
        ratio = limit_up / max(limit_down + 1, 1)
        market_bull = ratio > 2
        if ratio > 5:
            score_adapt = 3.0
            findings.append(f"大盘情绪极度乐观，涨停{int(limit_up)}家/跌停{int(limit_down)}家，个股行情空间大")
        elif ratio > 2:
            score_adapt = 2.5
            findings.append(f"大盘情绪偏多，涨停{int(limit_up)}家/跌停{int(limit_down)}家，整体环境有利")
        elif ratio > 0.5:
            score_adapt = 2.0
            findings.append(f"大盘情绪中性，涨停{int(limit_up)}家/跌停{int(limit_down)}家，个股分化")
        else:
            score_adapt = 1.0
            findings.append(f"⚠️ 大盘情绪偏空，涨停{int(limit_up)}家/跌停{int(limit_down)}家，做多难度加大")

    if north_net_inflow is not None:
        if north_net_inflow > 10:
            findings.append(f"北向资金今日净流入 {fmt_number(north_net_inflow, 2)} 亿，外资看多A股")
            score_adapt = min(score_adapt + 0.3, 3.0)
        elif north_net_inflow < -10:
            findings.append(f"⚠️ 北向资金今日净流出 {fmt_number(abs(north_net_inflow), 2)} 亿，外资撤离信号")
            score_adapt = max(score_adapt - 0.3, 0.5)
        else:
            findings.append(f"北向资金流入/流出 {fmt_number(north_net_inflow, 2)} 亿，影响中性")

    # ── 走势独立性（3分）——个股是否跑赢大盘 ──
    score_independence = 1.5
    if pct_change is not None:
        if market_bull:
            if pct_change > 5:
                score_independence = 3.0
                findings.append(f"大盘上涨背景下个股涨 {pct_str(pct_change)}，超额表现突出，独立行情强")
            elif pct_change > 2:
                score_independence = 2.5
                findings.append(f"个股跑赢大盘，有一定独立行情")
            elif pct_change > 0:
                score_independence = 2.0
                findings.append(f"个股小幅上涨 {pct_str(pct_change)}，跟随大盘")
            else:
                score_independence = 1.0
                findings.append(f"⚠️ 大盘向好但个股下跌 {pct_str(pct_change)}，个股走势偏弱")
        else:
            if pct_change > 2:
                score_independence = 3.0
                findings.append(f"大盘弱势中个股逆势上涨 {pct_str(pct_change)}，独立行情极强")
            elif pct_change > 0:
                score_independence = 2.5
                findings.append(f"大盘偏弱但个股守住涨幅，相对抗跌")
            elif pct_change > -2:
                score_independence = 2.0
                findings.append(f"大盘下跌，个股跌幅 {pct_str(pct_change)}，表现中等")
            else:
                score_independence = 1.0
                findings.append(f"个股跌幅 {pct_str(pct_change)}，抗跌性弱")

    # ── 涨跌弹性性价比（4分）──
    score_elasticity = 2.0
    # 通过市值和PE判断弹性
    if market_cap is not None:
        if market_cap < 2e10:  # 200亿以下
            score_elasticity = 3.5
            findings.append("小市值标的，行情启动后弹性大，适合题材/成长型行情")
        elif market_cap < 1e11:  # 1000亿以下
            score_elasticity = 3.0
            findings.append("中市值标的，兼具弹性与稳定性")
        elif market_cap < 5e11:  # 5000亿以下
            score_elasticity = 2.5
            findings.append("大市值标的，弹性适中，波动相对稳定")
        else:
            score_elasticity = 2.0
            findings.append("超大市值蓝筹，弹性有限但资金安全性高")

    # 风格适配检查
    if pe_ttm and roe:
        style = "价值型" if pe_ttm < 20 and roe > 15 else "成长型" if pe_ttm > 30 and roe > 20 else "混合型"
        findings.append(f"个股风格定位：{style}，当前市场{'价值风格占优，适配' if style == '价值型' else '成长风格占优，适配' if style == '成长型' else '风格均衡，兼容性强'}")

    total = score_adapt + score_independence + score_elasticity
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M10",
        module_name="大盘联动与市场风格适配",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice=f"短线：大盘{'偏多，积极做多' if market_bull else '偏空，控制仓位，谨慎追高'}",
        mid_advice="中线：关注北向资金持续净流入方向，判断外资主导的风格切换",
        long_advice="长线：大盘趋势决定个股天花板，在确认性牛市中加大仓位",
        conclusion=f"大盘适配评分 {total:.1f}/10，今日{'大盘偏多' if market_bull else '大盘偏空'}，个股表现 {pct_str(pct_change)}",
        detail={
            "market_bull": market_bull,
            "pct_change": pct_change,
            "north_net_inflow": north_net_inflow,
            "limit_up": limit_up,
            "limit_down": limit_down,
        },
    )
