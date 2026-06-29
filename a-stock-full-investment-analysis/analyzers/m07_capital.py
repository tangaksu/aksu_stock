"""M07 资金筹码深度博弈分析"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt, yi


def analyze_capital(data: dict) -> ModuleResult:
    fund_flow = data.get("fund_flow") or {}
    dragon = data.get("dragon_tiger") or []
    rt = data.get("realtime") or {}

    findings = []
    warnings = []
    score = 5.0

    # ── 主力资金流向 ──
    main_net = fund_flow.get("main_net")
    main_net_pct = fund_flow.get("main_net_pct")
    super_big = fund_flow.get("super_big_net")
    big_net = fund_flow.get("big_net")
    small_net = fund_flow.get("small_net")
    date = fund_flow.get("date", "")

    if main_net is not None:
        findings.append(f"【{date}】主力净流入：{yi(main_net)}（占比 {fmt(main_net_pct)}%）")
        if main_net > 0:
            score += min(2.5, main_net / 1e8 * 0.5)  # 每亿净流入加0.5分，上限2.5分
            if main_net > 5e8:
                findings.append("✅ 超级主力净流入 > 5亿，机构资金大力介入")
            elif main_net > 1e8:
                findings.append("✅ 主力净流入 > 1亿，资金积极布局")
            else:
                findings.append("✅ 主力小额净流入，温和做多")
        else:
            score += max(-2.5, main_net / 1e8 * 0.5)  # 净流出扣分
            if main_net < -5e8:
                warnings.append("🚨 主力净流出 > 5亿，大资金出逃信号")
            elif main_net < -1e8:
                warnings.append("⚠️ 主力净流出 > 1亿，主力撤退")
            else:
                findings.append("⚠️ 主力小额净流出，观望为主")

    if super_big is not None:
        findings.append(f"超大单净流入：{yi(super_big)}，大单净流入：{yi(big_net)}")
        if super_big and super_big > 0 and big_net and big_net > 0:
            score += 0.5
            findings.append("✅ 超大单与大单同向净流入，机构共识买入")

    if small_net is not None:
        findings.append(f"散户小单净流入：{yi(small_net)}")
        if small_net and small_net > 0 and main_net and main_net < 0:
            warnings.append("⚠️ 主力出货、散户接盘，分歧明显，慎追")

    # ── 近5/10/30日累计资金流向 ──
    recent = fund_flow.get("recent") or []
    if len(recent) >= 3:
        def _get_main_net(row):
            # 兼容原始中文键和归一化英文键
            for key in ("主力净流入-净额", "main_net"):
                v = row.get(key)
                if v is not None:
                    try:
                        f = float(v)
                        import math
                        return f if not math.isnan(f) else 0
                    except (TypeError, ValueError):
                        pass
            return 0
        total_5d = sum(_get_main_net(r) for r in recent[:5])
        total_10d = sum(_get_main_net(r) for r in recent[:10]) if len(recent) >= 10 else None
        total_30d = sum(_get_main_net(r) for r in recent[:30]) if len(recent) >= 30 else None
        findings.append(f"近5日主力累计净流入：{yi(total_5d)}")
        if total_10d is not None:
            findings.append(f"近10日主力累计净流入：{yi(total_10d)}")
        if total_30d is not None:
            findings.append(f"近30日主力累计净流入：{yi(total_30d)}")

        # 连续流向趋势判断
        recent5_nets = [_get_main_net(r) for r in recent[:5]]
        inflow_days = sum(1 for n in recent5_nets if n > 0)
        outflow_days = sum(1 for n in recent5_nets if n < 0)
        findings.append(f"近5日中：净流入 {inflow_days} 天，净流出 {outflow_days} 天")

        if total_5d > 0:
            score += 0.5
            if inflow_days >= 4:
                findings.append("✅ 近5日持续净流入，筹码积累信号")
            else:
                findings.append("✅ 近5日整体净流入，资金小幅布局")
        else:
            if outflow_days >= 4:
                findings.append("⚠️ 近5日持续净流出，主力不认可当前价格")
            else:
                findings.append("⚠️ 近5日整体净流出，资金偏谨慎")

    # ── 龙虎榜分析 ──
    if dragon:
        findings.append(f"近30日共 {len(dragon)} 次上龙虎榜")
        total_buy = sum(d.get("buy_total") or 0 for d in dragon)
        total_sell = sum(d.get("sell_total") or 0 for d in dragon)
        total_net = sum(d.get("net") or 0 for d in dragon)

        findings.append(f"龙虎榜买方合计：{yi(total_buy)}，卖方合计：{yi(total_sell)}，净额：{yi(total_net)}")

        reasons = [d.get("reason", "") for d in dragon if d.get("reason")]
        if any("连续涨停" in r or "涨幅偏大" in r for r in reasons):
            findings.append("ℹ️ 龙虎榜因涨幅偏大上榜，注意游资博弈风险")
        if any("异动" in r or "跌幅" in r for r in reasons):
            warnings.append("⚠️ 龙虎榜因大跌上榜，关注资金出逃方向")

        if total_net and total_net > 0:
            score += 0.5
            findings.append("✅ 龙虎榜净买入，游资做多信号")
        elif total_net and total_net < 0:
            score -= 0.5

    # ── 主力操盘阶段判断 ──
    pct = rt.get("pct_change") or 0
    if main_net and main_net > 0 and pct < -1:
        stage = "洗盘阶段（主力压价吸筹）"
        score += 0.5
        findings.append(f"🔍 判断：{stage} — 跌时主力净流入，是洗盘不是出货")
    elif main_net and main_net > 0 and pct > 2:
        stage = "拉升阶段（主力联动上攻）"
        score += 1.0
        findings.append(f"🔍 判断：{stage} — 主力加速入场，强势做多")
    elif main_net and main_net < 0 and pct > 3:
        stage = "派发阶段（借涨出货）"
        score -= 1.0
        warnings.append(f"🔍 判断：{stage} — 涨时主力净流出，高度警惕出货陷阱")
    elif main_net and main_net < 0 and pct < -2:
        stage = "加速离场（主力撤退）"
        score -= 1.5
        warnings.append(f"🔍 判断：{stage} — 价跌量增且主力净流出，避免接盘")
    else:
        stage = "方向不明（观察蓄势）"

    score = min(10.0, max(1.0, score))
    all_findings = findings + warnings
    conclusion = f"主力资金态势：{stage}。{'建议顺势跟随主力方向操作。' if score >= 6 else '主力资金未形成明确做多信号，建议谨慎。'}"

    return ModuleResult(
        module_id="M07",
        module_name="资金筹码深度博弈分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice=f"短线跟踪超大单方向，{stage}期间{'顺势跟进' if score >= 6 else '观望为主'}",
        mid_advice="中线以5日累计净流入方向为主要参考，持续流入可持有",
        long_advice="长线以基本面为主，资金面为辅助验证",
        conclusion=conclusion,
        detail={"fund_flow": fund_flow, "dragon_count": len(dragon), "stage": stage},
    )
