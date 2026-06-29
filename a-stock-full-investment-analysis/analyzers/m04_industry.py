"""M04 行业周期与产业链景气度分析"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt, pct_fmt


def analyze_industry(data: dict) -> ModuleResult:
    info = data.get("stock_info") or {}
    peers = data.get("industry_peers") or []
    sentiment = data.get("market_sentiment") or {}
    rt = data.get("realtime") or {}

    findings = []
    score = 5.0

    industry = info.get("industry", "")
    if not industry:
        findings.append("⚠️ 所属行业：数据获取失败（接口暂未返回行业信息，可能为新股或接口限制）")
    else:
        findings.append(f"所属行业：{industry}")

    # ── 行业类型判断 ──
    cycle_type = "均衡型"
    cycle_stage = "不明"
    policy_support = False

    policy_industries = [
        "新能源", "半导体", "芯片", "AI", "人工智能", "光伏", "储能",
        "军工", "国防", "医疗器械", "创新药", "数字经济", "云计算",
        "机器人", "谐波", "减速器", "工业自动化", "智能制造",
    ]
    defensive_industries = [
        "白酒", "食品饮料", "消费", "公用事业", "医药", "水务",
    ]
    cyclical_industries = [
        "钢铁", "煤炭", "化工", "有色金属", "房地产", "建材",
        "航运", "造纸",
    ]

    for k in policy_industries:
        if k in industry:
            cycle_type = "成长赛道"
            policy_support = True
            score += 1.5
            findings.append(f"✅ {industry} 属于政策重点支持成长赛道")
            break

    if cycle_type == "均衡型":
        for k in defensive_industries:
            if k in industry:
                cycle_type = "防御消费"
                score += 0.5
                findings.append(f"✅ {industry} 属于防御型消费行业，抗周期性较强")
                break

    if cycle_type == "均衡型":
        for k in cyclical_industries:
            if k in industry:
                cycle_type = "强周期"
                findings.append(f"⚠️ {industry} 属于强周期行业，需关注景气度拐点")
                break

    # ── 同业对比（判断行业当前景气度） ──
    if peers:
        up_count = sum(1 for p in peers if (p.get("pct") or 0) > 0)
        down_count = sum(1 for p in peers if (p.get("pct") or 0) < 0)
        avg_pct = sum(p.get("pct") or 0 for p in peers) / len(peers)

        findings.append(
            f"行业内 {len(peers)} 只股票：涨{up_count}跌{down_count}，"
            f"行业平均涨幅：{avg_pct:+.2f}%"
        )

        if avg_pct > 2:
            score += 1.5
            cycle_stage = "景气上行"
            findings.append("✅ 行业整体强势上行，板块景气度高")
        elif avg_pct > 0:
            score += 0.5
            cycle_stage = "温和向好"
        elif avg_pct < -2:
            score -= 1.0
            cycle_stage = "景气下行"
            findings.append("⚠️ 行业整体走弱，板块承压")
        else:
            cycle_stage = "震荡整理"

        # ── 行业PE/PB均值（与个股对比）──
        pe_vals = [p.get("pe") for p in peers if p.get("pe") and p.get("pe") > 0 and p.get("pe") < 2000]
        pb_vals = [p.get("pb") for p in peers if p.get("pb") and p.get("pb") > 0]
        if pe_vals:
            avg_pe = sum(pe_vals) / len(pe_vals)
            pe_vals_sorted = sorted(pe_vals)
            median_pe = pe_vals_sorted[len(pe_vals_sorted) // 2]
            findings.append(f"行业平均PE：{avg_pe:.1f}x（中位数 {median_pe:.1f}x，样本 {len(pe_vals)} 只）")
            # 个股PE与行业对比
            stock_pe_str = rt.get("pe_ttm") or info.get("pe_ttm", "")
            try:
                stock_pe = float(str(stock_pe_str).replace(",", "")) if stock_pe_str else None
            except Exception:
                stock_pe = None
            if stock_pe and stock_pe > 0:
                pe_premium = (stock_pe - median_pe) / median_pe * 100 if median_pe > 0 else None
                if pe_premium is not None:
                    if pe_premium > 50:
                        findings.append(f"⚠️ 个股PE ({stock_pe:.1f}x) 较行业中位数溢价 {pe_premium:.0f}%，估值明显偏贵")
                    elif pe_premium > 20:
                        findings.append(f"ℹ️ 个股PE ({stock_pe:.1f}x) 较行业中位数溢价 {pe_premium:.0f}%，略偏高")
                    elif pe_premium < -20:
                        score += 0.5
                        findings.append(f"✅ 个股PE ({stock_pe:.1f}x) 较行业中位数折价 {abs(pe_premium):.0f}%，行业内低估")
            if avg_pe > 100:
                findings.append("⚠️ 行业整体估值偏高，需业绩持续兑现支撑")
            elif avg_pe < 15:
                score += 0.5
                findings.append("✅ 行业低估值，价值洼地机会")

        if pb_vals:
            avg_pb = sum(pb_vals) / len(pb_vals)
            findings.append(f"行业平均PB：{avg_pb:.2f}x")

    # ── 大盘情绪对行业的影响 ──
    mood = sentiment.get("mood_score")
    if mood:
        if mood > 60:
            score += 0.5
            findings.append(f"✅ 市场情绪偏多（涨家占比{mood:.0f}%），行业Beta收益可期")
        elif mood < 40:
            score -= 0.5
            findings.append(f"⚠️ 市场情绪偏空（涨家占比{mood:.0f}%），防御为主")

    score = min(10.0, max(1.0, score))

    conclusion = (
        f"{industry or '未知行业'}（{cycle_type}）当前景气度：{cycle_stage}。"
        f"{'政策重点支持，行业β向上。' if policy_support else '关注行业库存与需求拐点。'}"
    )

    return ModuleResult(
        module_id="M04",
        module_name="行业周期与产业链景气度分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice=f"关注 {industry or '所属板块'} 板块联动，景气上行期优先持有行业龙头",
        mid_advice=f"中线重点跟踪 {industry or '行业'} 政策落地进度与产能变化",
        long_advice=f"{'成长赛道长期持有价值显著，关注行业格局集中度提升' if cycle_type == '成长赛道' else '周期类标的中长线需匹配景气周期高点减仓'}",
        conclusion=conclusion,
        detail={"industry": industry, "cycle_type": cycle_type, "cycle_stage": cycle_stage, "peers_count": len(peers)},
    )
