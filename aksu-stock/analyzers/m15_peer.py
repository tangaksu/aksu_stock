"""M15 — 同业对标与智能选股参考（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_peer(data: dict) -> ModuleResult:
    code = data.get("code", "")
    name = data.get("name") or code
    industry = data.get("industry") or "未知行业"
    industry_peers = data.get("industry_peers") or []
    pe_ttm = safe_float(data.get("pe_ttm"))
    market_cap = safe_float(data.get("market_cap"))
    roe = safe_float(data.get("roe"))
    profit_yoy = safe_float(data.get("profit_yoy"))
    pct_change = safe_float(data.get("pct_change"))
    main_net_inflow = safe_float(data.get("main_net_inflow"))

    findings: list[str] = []

    # ── 行业综合竞争力（10分满分）——7维横向对比 ──
    score_total = 5.0
    comparison_rows: list[dict] = []
    rivals: list[dict] = []

    if industry_peers:
        # 剔除自身
        peers = [p for p in industry_peers if str(p.get("code", "")) != code][:5]
        rivals = peers

        # 计算同业均值
        peer_pes = [safe_float(p.get("pe_ttm")) for p in peers if safe_float(p.get("pe_ttm")) and safe_float(p.get("pe_ttm"), 0) > 0]
        peer_caps = [safe_float(p.get("market_cap")) for p in peers if safe_float(p.get("market_cap"))]
        peer_pcts = [safe_float(p.get("pct_change")) for p in peers if safe_float(p.get("pct_change")) is not None]

        avg_peer_pe = sum(peer_pes) / len(peer_pes) if peer_pes else None
        avg_peer_cap = sum(peer_caps) / len(peer_caps) if peer_caps else None
        avg_peer_pct = sum(peer_pcts) / len(peer_pcts) if peer_pcts else None

        # 估值对比
        if pe_ttm and avg_peer_pe and avg_peer_pe > 0:
            pe_vs = (avg_peer_pe - pe_ttm) / avg_peer_pe * 100
            if pe_vs > 20:
                score_total = min(score_total + 1.5, 10.0)
                findings.append(f"估值优势：PE {pe_ttm:.1f}x，低于同业均值 {avg_peer_pe:.1f}x（折价 {pe_vs:.1f}%）")
            elif pe_vs < -20:
                score_total = max(score_total - 0.5, 1.0)
                findings.append(f"估值劣势：PE {pe_ttm:.1f}x，高于同业均值 {avg_peer_pe:.1f}x")
            else:
                findings.append(f"估值与同业持平：PE {pe_ttm:.1f}x vs 同业 {avg_peer_pe:.1f}x")

        # 市值对比（判断行业梯队）
        if market_cap and peer_caps:
            rank = sum(1 for c in peer_caps if c > market_cap) + 1
            tier = "龙头" if rank == 1 else "第二梯队" if rank <= 3 else "第三梯队"
            findings.append(f"市值排名：同业第 {rank} 位，属于行业【{tier}】")
            if rank == 1:
                score_total = min(score_total + 1.0, 10.0)
            elif rank <= 3:
                score_total = min(score_total + 0.5, 10.0)

        # 今日走势强弱
        if pct_change is not None and avg_peer_pct is not None:
            excess = pct_change - avg_peer_pct
            if excess > 2:
                score_total = min(score_total + 0.5, 10.0)
                findings.append(f"今日相对同业超额 +{excess:.2f}%，走势明显强于同业")
            elif excess > 0:
                findings.append(f"今日相对同业超额 +{excess:.2f}%，走势略强")
            elif excess < -2:
                score_total = max(score_total - 0.3, 1.0)
                findings.append(f"今日相对同业弱势 {excess:.2f}%，走势偏弱")
            else:
                findings.append(f"今日表现与同业基本持平（相对超额 {excess:.2f}%）")

        # 构建对比表
        for p in peers[:5]:
            comparison_rows.append({
                "code": str(p.get("code", "")),
                "name": str(p.get("name", "")),
                "price": safe_float(p.get("price")),
                "pct_change": safe_float(p.get("pct_change")),
                "pe_ttm": safe_float(p.get("pe_ttm")),
                "market_cap_yi": safe_float(p.get("market_cap")) / 1e8 if safe_float(p.get("market_cap")) else None,
            })
    else:
        findings.append(f"⚠️ 【{industry}】行业同业数据获取失败，建议手动在同花顺行业板块查询对比")

    # ROE 盈利能力对比（基于自身ROE判断）
    if roe is not None:
        if roe > 20:
            score_total = min(score_total + 1.0, 10.0)
            findings.append(f"ROE {pct_str(roe)}（>20%），盈利能力行业领先")
        elif roe > 15:
            score_total = min(score_total + 0.5, 10.0)
            findings.append(f"ROE {pct_str(roe)}，盈利能力良好")
        elif roe < 8:
            score_total = max(score_total - 0.5, 1.0)
            findings.append(f"ROE {pct_str(roe)}（<8%），盈利能力偏弱")

    # 资金面认可度
    if main_net_inflow and main_net_inflow > 1e7:
        score_total = min(score_total + 0.5, 10.0)
        findings.append("主力资金净流入，资金面相对同业更受认可")

    score_total = round(max(1.0, min(10.0, score_total)), 2)
    stars = score_to_stars(score_total)

    # 替代标的推荐逻辑
    substitutes = ""
    if rivals and score_total < 6:
        better = [p for p in rivals if safe_float(p.get("pe_ttm")) and safe_float(p.get("pe_ttm"), 0) > 0 and
                  (pe_ttm is None or safe_float(p.get("pe_ttm")) < pe_ttm)][:2]
        if better:
            names = ", ".join([f"{p.get('name')}({p.get('code')})" for p in better])
            substitutes = f"性价比参考替代标的：{names}"

    return ModuleResult(
        module_id="M15",
        module_name="同业对标与智能选股",
        score=score_total,
        stars=stars,
        key_findings=findings[:5],
        short_advice="短线：选择行业中今日走势最强的标的做T，获得超额收益",
        mid_advice="中线：优先选择PE低于行业均值+ROE高于行业均值的标的",
        long_advice=f"长线：{substitutes if substitutes else '当前标的在行业中具备竞争力，可作为核心配置'}",
        conclusion=f"同业竞争力评分 {score_total:.1f}/10，行业【{industry}】，与同业对比{'具备优势' if score_total >= 6.5 else '表现一般' if score_total >= 5 else '存在劣势'}",
        detail={
            "industry": industry,
            "comparison_rows": comparison_rows,
            "rivals": rivals[:3],
            "substitutes": substitutes,
        },
    )
