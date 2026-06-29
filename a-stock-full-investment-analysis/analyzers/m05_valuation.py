"""M05 估值定价与护城河壁垒分析"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt


def analyze_valuation(data: dict) -> ModuleResult:
    rt = data.get("realtime") or {}
    info = data.get("stock_info") or {}
    vh = data.get("valuation_history") or {}
    fi = data.get("financial_indicator") or {}
    profits = data.get("profit_statement") or []

    findings = []
    warnings = []
    score = 5.0

    # ── 当前估值 ──
    pe = None
    pb = None

    # 优先取实时数据中的PE/PB，再取基本信息
    pe_str = rt.get("pe_ttm") or info.get("pe_ttm", "")
    pb_str = rt.get("pb") or info.get("pb", "")

    try:
        pe = float(str(pe_str).replace(",", "")) if pe_str else None
    except Exception:
        pass
    try:
        pb = float(str(pb_str).replace(",", "")) if pb_str else None
    except Exception:
        pass

    if pe:
        findings.append(f"PE-TTM：{pe:.1f}x")
    if pb:
        findings.append(f"PB：{pb:.2f}x")

    industry = info.get("industry", "")

    # ── 行业适配估值判断 ──
    if pe:
        if any(k in industry for k in ["白酒", "消费", "医药", "品牌"]):
            # 消费医药合理PE 20-40x
            if pe < 20:
                score += 2.0
                findings.append("✅ 消费/医药股PE < 20x，深度低估，具备明显安全边际")
            elif pe < 35:
                score += 1.0
                findings.append("✅ 消费/医药股估值合理（20-35x PE）")
            elif pe < 60:
                findings.append("⚠️ 消费/医药股估值偏高（35-60x PE），需业绩持续增长支撑")
                score -= 0.5
            else:
                score -= 1.5
                warnings.append(f"🚨 消费/医药股PE={pe:.0f}x，估值泡沫明显")

        elif any(k in industry for k in ["科技", "芯片", "AI", "软件", "互联网"]):
            # 科技股用PEG评估更合理
            roe = fi.get("roe")
            if pe < 30:
                score += 1.5
                findings.append("✅ 科技股PE < 30x，估值合理偏低")
            elif pe < 80:
                score += 0.5
                findings.append("ℹ️ 科技股PE在合理区间（30-80x）")
            else:
                findings.append("⚠️ 科技股PE > 80x，需高增速支撑")
                score -= 0.5

        elif any(k in industry for k in ["钢铁", "煤炭", "化工", "有色"]):
            # 周期股用PB更合适
            if pb:
                if pb < 1.0:
                    score += 2.0
                    findings.append("✅ 周期股PB < 1.0x，破净低估，底部布局机会")
                elif pb < 1.5:
                    score += 1.0
                    findings.append("✅ 周期股PB合理（1.0-1.5x）")
                else:
                    findings.append("⚠️ 周期股PB偏高，需关注景气度是否见顶")

        else:
            # 通用PE估值
            if pe < 15:
                score += 2.0
                findings.append(f"✅ PE < 15x，估值极低，安全边际充裕")
            elif pe < 25:
                score += 1.0
                findings.append(f"✅ PE 15-25x，估值合理")
            elif pe < 40:
                findings.append(f"⚠️ PE 25-40x，估值偏高")
                score -= 0.5
            else:
                score -= 1.5
                warnings.append(f"🚨 PE > 40x，估值偏贵")

    # ── 历史估值分位 ──
    if vh:
        pe_pct = vh.get("pe_percentile")
        current_pe = vh.get("current_pe")
        pe_min = vh.get("pe_min")
        pe_max = vh.get("pe_max")
        pe_avg = vh.get("pe_avg")
        pb_pct = vh.get("pb_percentile")

        if pe_pct is not None:
            findings.append(
                f"历史PE分位（数据来源：东财指标库）：{pe_pct:.0f}% "
                f"（区间 {pe_min:.1f}x ~ {pe_max:.1f}x，均值 {pe_avg:.1f}x）"
            )
            if pe_pct < 20:
                score += 1.5
                findings.append("✅ 估值处于历史底部20%分位，极度低估")
            elif pe_pct < 40:
                score += 0.5
                findings.append("✅ 估值处于历史低位（20-40%分位）")
            elif pe_pct > 80:
                score -= 1.5
                warnings.append(f"🚨 估值处于历史高位（{pe_pct:.0f}%分位），接近历史峰值")
            elif pe_pct > 60:
                score -= 0.5
                findings.append(f"⚠️ 估值偏历史高位（{pe_pct:.0f}%分位）")
        if pb_pct is not None:
            findings.append(f"历史PB分位：{pb_pct:.0f}%")
    else:
        findings.append("ℹ️ 历史估值分位数据暂缺，仅凭当前PE/PB评估")

    # ── 行业估值对标 ──
    peers = data.get("industry_peers") or []
    if peers and pe:
        peer_pe_vals = [p.get("pe") for p in peers if p.get("pe") and 0 < p.get("pe") < 2000]
        if peer_pe_vals:
            peer_pe_sorted = sorted(peer_pe_vals)
            peer_pe_median = peer_pe_sorted[len(peer_pe_sorted) // 2]
            peer_pe_avg = sum(peer_pe_vals) / len(peer_pe_vals)
            pe_vs_peer = (pe - peer_pe_median) / peer_pe_median * 100 if peer_pe_median > 0 else None
            findings.append(
                f"行业对标：行业PE中位数 {peer_pe_median:.1f}x（均值 {peer_pe_avg:.1f}x，"
                f"数据来源：同行业 {len(peer_pe_vals)} 只可比公司）"
            )
            if pe_vs_peer is not None:
                if pe_vs_peer > 100:
                    warnings.append(f"🚨 个股PE较行业中位数溢价 {pe_vs_peer:.0f}%，估值显著偏贵")
                    score -= 1.0
                elif pe_vs_peer > 30:
                    findings.append(f"⚠️ 个股PE较行业中位数溢价 {pe_vs_peer:.0f}%，估值偏高")
                elif pe_vs_peer < -30:
                    score += 0.5
                    findings.append(f"✅ 个股PE较行业中位数折价 {abs(pe_vs_peer):.0f}%，行业内相对低估")

    # ── 护城河评估 ──
    moat_score = 0
    moat_findings = []
    gross_margin = fi.get("gross_margin")
    roe = fi.get("roe")

    if gross_margin:
        if gross_margin > 50:
            moat_score += 2
            moat_findings.append(f"✅ 毛利率 {gross_margin:.1f}%（>50%），品牌/技术护城河宽")
        elif gross_margin > 30:
            moat_score += 1
            moat_findings.append(f"✅ 毛利率 {gross_margin:.1f}%，具有一定议价权")
        elif gross_margin < 10:
            moat_findings.append(f"⚠️ 毛利率 {gross_margin:.1f}%，产品同质化，竞争激烈")

    if roe:
        if roe > 20:
            moat_score += 2
            moat_findings.append(f"✅ ROE {roe:.1f}%（>20%），超额收益能力持续，护城河坚实")
        elif roe > 15:
            moat_score += 1
            moat_findings.append(f"✅ ROE {roe:.1f}%，资本回报稳定")

    findings.extend(moat_findings)
    score += moat_score * 0.3

    score = min(10.0, max(1.0, score))

    # 定价区间
    if score >= 8:
        val_zone = "深度低估"
        strategy = "分批低吸，优先配置"
    elif score >= 7:
        val_zone = "合理低估"
        strategy = "逢回调布局，持有为主"
    elif score >= 5:
        val_zone = "估值合理"
        strategy = "持股待涨，不追高"
    elif score >= 3:
        val_zone = "轻度高估"
        strategy = "分批减仓，控制仓位"
    else:
        val_zone = "重度泡沫"
        strategy = "清仓规避，等待回调"

    all_findings = findings + warnings
    conclusion = f"估值区间：{val_zone}。操作建议：{strategy}。"

    return ModuleResult(
        module_id="M05",
        module_name="估值定价与护城河壁垒分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice=f"当前{val_zone}，{'短线可适当配置' if score >= 6 else '短线暂不追高'}",
        mid_advice=f"中线{strategy}",
        long_advice=f"护城河{'宽阔' if moat_score >= 3 else '一般'}，长线{'持有价值显著' if moat_score >= 3 else '需跟踪竞争格局变化'}",
        conclusion=conclusion,
        detail={"pe": pe, "pb": pb, "valuation_history": vh, "moat_score": moat_score},
    )
