"""M05 — 估值定价与护城河壁垒分析（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_valuation(data: dict) -> ModuleResult:
    pe_ttm = safe_float(data.get("pe_ttm"))
    pb = safe_float(data.get("pb"))
    roe = safe_float(data.get("roe"))
    profit_yoy = safe_float(data.get("profit_yoy"))
    gross_margin = safe_float(data.get("gross_margin"))
    dividend_yield = safe_float(data.get("dividend_yield"))
    price = safe_float(data.get("price"))
    avg_target_price = safe_float(data.get("avg_target_price"))
    week52_high = safe_float(data.get("week52_high"))
    week52_low = safe_float(data.get("week52_low"))
    week52_position = safe_float(data.get("week52_position"))
    industry_peers = data.get("industry_peers") or []
    kline_df = data.get("kline_df")

    findings: list[str] = []

    # ── 估值安全边际（3分）──
    score_safety = 1.5
    if pe_ttm is not None and pe_ttm > 0:
        if pe_ttm < 15:
            score_safety = 3.0
            findings.append(f"PE-TTM {fmt_number(pe_ttm, 1)}x，估值偏低，安全边际充足")
        elif pe_ttm < 25:
            score_safety = 2.5
            findings.append(f"PE-TTM {fmt_number(pe_ttm, 1)}x，估值合理")
        elif pe_ttm < 40:
            score_safety = 2.0
            findings.append(f"PE-TTM {fmt_number(pe_ttm, 1)}x，估值中等，成长性可支撑")
        elif pe_ttm < 60:
            score_safety = 1.5
            findings.append(f"PE-TTM {fmt_number(pe_ttm, 1)}x，估值偏高，依赖业绩兑现")
        else:
            score_safety = 0.8
            findings.append(f"⚠️ PE-TTM {fmt_number(pe_ttm, 1)}x，估值极高，泡沫风险大")
    elif pe_ttm is not None and pe_ttm < 0:
        score_safety = 0.5
        findings.append(f"⚠️ PE-TTM 为负（{fmt_number(pe_ttm, 1)}x），当前处于亏损状态")
    else:
        findings.append("PE-TTM 数据暂缺，使用PB/PS等指标替代评估")

    if pb is not None:
        if pb < 1:
            # 破净可能是深度低估，也可能反映资产减值或负净资产问题，需结合其他指标综合判断
            findings.append(f"PB {fmt_number(pb, 2)}x，破净标的，静态估值低廉（注意排查资产质量风险）")
            score_safety = min(score_safety + 0.3, 3.0)
        elif pb < 2:
            findings.append(f"PB {fmt_number(pb, 2)}x，市净率合理")
        else:
            findings.append(f"PB {fmt_number(pb, 2)}x，资产溢价明显")

    # ── 估值性价比（2分）——行业对比与机构目标价 ──
    score_value = 1.0
    if industry_peers and pe_ttm and pe_ttm > 0:
        peer_pes = [safe_float(p.get("pe_ttm")) for p in industry_peers if safe_float(p.get("pe_ttm")) and safe_float(p.get("pe_ttm")) > 0]
        if peer_pes:
            avg_peer_pe = sum(peer_pes) / len(peer_pes)
            discount = (avg_peer_pe - pe_ttm) / avg_peer_pe * 100
            if discount > 20:
                score_value = 2.0
                findings.append(f"估值显著低于同业（行业均值PE {avg_peer_pe:.1f}x，折价 {discount:.1f}%），估值性价比突出")
            elif discount > 0:
                score_value = 1.7
                findings.append(f"估值低于同业均值（行业PE {avg_peer_pe:.1f}x），有一定估值优势")
            elif discount > -20:
                score_value = 1.3
                findings.append(f"估值与同业持平（行业PE {avg_peer_pe:.1f}x），无明显折溢价")
            else:
                score_value = 0.8
                findings.append(f"⚠️ 估值显著高于同业（行业PE {avg_peer_pe:.1f}x，溢价 {-discount:.1f}%），需要更强业绩支撑")

    if avg_target_price and price and price > 0:
        upside = (avg_target_price - price) / price * 100
        findings.append(f"机构平均目标价 {fmt_number(avg_target_price, 2)}，较现价潜在空间 {pct_str(upside)}")
        if upside > 30:
            score_value = min(score_value + 0.3, 2.0)
        elif upside < -10:
            score_value = max(score_value - 0.3, 0.5)

    # ── 护城河厚度（3分）──
    score_moat = 1.5
    moat_items: list[str] = []
    if gross_margin is not None:
        if gross_margin > 60:
            score_moat = 3.0
            moat_items.append(f"毛利率 {pct_str(gross_margin)}（极高，护城河宽厚）")
        elif gross_margin > 40:
            score_moat = 2.5
            moat_items.append(f"毛利率 {pct_str(gross_margin)}（较高，具备竞争优势）")
        elif gross_margin > 25:
            score_moat = 2.0
            moat_items.append(f"毛利率 {pct_str(gross_margin)}（中等）")
        else:
            score_moat = 1.5
            moat_items.append(f"毛利率 {pct_str(gross_margin)}（偏低，竞争激烈）")
    if roe is not None:
        if roe > 25:
            moat_items.append(f"ROE {pct_str(roe)}（高ROE证明护城河有效）")
            score_moat = min(score_moat + 0.3, 3.0)
        elif roe > 15:
            moat_items.append(f"ROE {pct_str(roe)}（良好）")
    if moat_items:
        findings.append("护城河：" + "，".join(moat_items))

    # ── 长期定价权（2分）──
    score_pricing = 1.5
    if profit_yoy is not None and gross_margin is not None:
        if profit_yoy > 15 and gross_margin > 35:
            score_pricing = 2.0
            findings.append("业绩增速+毛利率双优，具备长期定价权")
        elif profit_yoy > 0:
            score_pricing = 1.7
    # PEG
    if pe_ttm and pe_ttm > 0 and profit_yoy and profit_yoy > 0:
        peg = pe_ttm / profit_yoy
        findings.append(f"PEG = {peg:.2f}（{'低估' if peg < 1 else '合理' if peg < 2 else '偏高'}）")
        if peg < 1:
            score_pricing = min(score_pricing + 0.3, 2.0)

    # 52周位置分析
    if week52_position is not None:
        if week52_position < 30:
            findings.append(f"52周价格位置 {week52_position:.1f}%（处于历史低位区间，布局机会）")
            score_safety = min(score_safety + 0.2, 3.0)
        elif week52_position > 80:
            findings.append(f"⚠️ 52周价格位置 {week52_position:.1f}%（处于历史高位，追高风险大）")
            score_safety = max(score_safety - 0.2, 0.5)
        else:
            findings.append(f"52周价格位置 {week52_position:.1f}%（中部区间）")

    total = score_safety + score_value + score_moat + score_pricing
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    # 区间判断
    if total >= 8:
        zone = "深度低估"
    elif total >= 6.5:
        zone = "合理低估"
    elif total >= 5:
        zone = "估值合理"
    elif total >= 3.5:
        zone = "轻度高估"
    else:
        zone = "重度泡沫"

    return ModuleResult(
        module_id="M05",
        module_name="估值定价与护城河壁垒",
        score=total,
        stars=stars,
        key_findings=findings[:6],
        short_advice=f"短线：{'当前估值偏高，不宜追涨' if score_safety < 1.5 else '估值合理，短线可关注技术支撑位入场'}",
        mid_advice=f"中线：当前估值区间【{zone}】，{'可分批低吸' if zone in ['深度低估', '合理低估'] else '持有待涨' if zone == '估值合理' else '建议分批减仓'}",
        long_advice=f"长线：PE {fmt_number(pe_ttm, 1)}x + 毛利率 {pct_str(gross_margin)}，{'核心资产，长期持有' if score_moat >= 2.5 else '普通标的，跟踪业绩变化'}",
        conclusion=f"估值定价区间：【{zone}】，PE-TTM {fmt_number(pe_ttm, 1)}x，综合估值评分 {total:.1f}/10",
        detail={
            "pe_ttm": pe_ttm, "pb": pb, "roe": roe, "gross_margin": gross_margin,
            "week52_position": week52_position, "valuation_zone": zone,
            "avg_target_price": avg_target_price,
        },
    )
