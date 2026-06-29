"""M15 同业对标与智能选股参考"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt


def analyze_peer(data: dict) -> ModuleResult:
    peers = data.get("industry_peers") or []
    rt = data.get("realtime") or {}
    info = data.get("stock_info") or {}
    fi = data.get("financial_indicator") or {}

    findings = []
    score = 5.0

    code = data.get("code", "")
    current_price = rt.get("price")
    current_name = rt.get("name") or info.get("name", code)
    industry = info.get("industry", "")
    current_pct = rt.get("pct_change") or 0

    # 当前PE/PB
    try:
        current_pe = float(str(info.get("pe_ttm", "") or "").replace(",", "")) or None
    except Exception:
        current_pe = None
    try:
        current_pb = float(str(info.get("pb", "") or "").replace(",", "")) or None
    except Exception:
        current_pb = None

    # ── 行业排名 ──
    if peers:
        # 按涨跌幅排序
        sorted_peers = sorted(peers, key=lambda x: x.get("pct") or 0, reverse=True)
        rank = next((i + 1 for i, p in enumerate(sorted_peers) if p.get("code") == code), None)

        findings.append(f"同行业 {len(peers)} 只标的横向对比（按今日涨跌幅排序）")

        if rank:
            findings.append(f"个股在行业今日涨跌幅排名：第 {rank}/{len(peers)} 位")
            if rank <= 3:
                score += 2.0
                findings.append("✅ 行业内涨幅领先（前3名），相对强势突出")
            elif rank <= len(peers) // 3:
                score += 1.0
                findings.append("✅ 行业内强于均值（前1/3）")
            elif rank > len(peers) * 2 // 3:
                score -= 1.0
                findings.append("⚠️ 行业内相对弱势（后1/3），关注是否有特殊利空")

        # 行业PE中位数对比
        pe_list = [p.get("pe") for p in peers if p.get("pe") and 0 < p.get("pe") < 300]
        if pe_list and current_pe:
            pe_median = sorted(pe_list)[len(pe_list) // 2]
            pe_discount = (current_pe - pe_median) / pe_median * 100
            findings.append(f"行业PE中位数：{pe_median:.1f}x，个股PE：{current_pe:.1f}x，溢价/折价：{pe_discount:+.1f}%")
            if pe_discount < -20:
                score += 1.5
                findings.append("✅ PE相对行业中值折价 > 20%，估值具备竞争优势")
            elif pe_discount < 0:
                score += 0.5
                findings.append("✅ PE低于行业均值，相对低估")
            elif pe_discount > 30:
                score -= 1.0
                findings.append("⚠️ PE高于行业均值30%+，溢价需要更强业绩支撑")

        # 市值梯队
        caps = [p.get("market_cap") or 0 for p in peers if p.get("market_cap")]
        if caps:
            sorted_caps = sorted(caps, reverse=True)
            try:
                current_cap_str = info.get("market_cap", "0").replace("亿", "").replace(",", "")
                current_cap = float(current_cap_str) * 1e8
                cap_rank = sum(1 for c in sorted_caps if c > current_cap) + 1
                findings.append(f"行业市值排名：第 {cap_rank}/{len(sorted_caps)} 位")
                if cap_rank <= 3:
                    score += 0.5
                    findings.append("✅ 行业龙头市值地位，机构资金优先配置")
            except Exception:
                pass

        # 展示同行业TOP3
        findings.append("--- 同行业涨幅TOP3 ---")
        for p in sorted_peers[:3]:
            findings.append(
                f"  {p.get('name', p.get('code', ''))}: "
                f"{fmt(p.get('price'))} ({(p.get('pct') or 0):+.2f}%) "
                f"PE={fmt(p.get('pe'))}x"
            )

    else:
        findings.append("⚠️ 未获取到同业对标数据，请手动查询行业排名")

    # ── 选股策略适配 ──
    roe = fi.get("roe")
    gross_margin = fi.get("gross_margin")

    strategies_matched = []
    if roe and roe >= 15 and gross_margin and gross_margin >= 30 and current_pe and current_pe < 30:
        strategies_matched.append("价值成长策略（ROE高+低估值）")
        score += 0.5

    if strategies_matched:
        findings.append(f"✅ 匹配选股策略：{' | '.join(strategies_matched)}")

    score = min(10.0, max(1.0, score))

    conclusion = (
        f"{current_name} 在 {industry} 行业中综合竞争力评分：{score:.1f}/10。"
        + (f"行业涨幅排名第{rank}位。" if peers and rank else "")
    )

    return ModuleResult(
        module_id="M15",
        module_name="同业对标与智能选股参考",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice="行业强势期优先选板块内强势龙头，弱势期选择估值最低的行业代表",
        mid_advice="PE相对行业折价20%以上且基本面不差的标的，中线布局性价比高",
        long_advice="优先布局行业市值前三的龙头，长线安全边际更高",
        conclusion=conclusion,
        detail={"peer_count": len(peers), "industry_rank": rank if peers else None},
    )
