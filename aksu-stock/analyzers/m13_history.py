"""M13 — 历史走势规律与周期复盘（满分10分）"""
from __future__ import annotations
from analyzers.base import ModuleResult, safe_float, score_to_stars, pct_str, fmt_number


def analyze_history(data: dict) -> ModuleResult:
    kline_df = data.get("kline_df")
    price = safe_float(data.get("price"))
    week52_high = safe_float(data.get("week52_high"))
    week52_low = safe_float(data.get("week52_low"))
    week52_position = safe_float(data.get("week52_position"))

    findings: list[str] = []

    # ── 周期规律稳定性（3分）──
    score_cycle = 1.5
    max_drawdown = None
    avg_up = None
    volatility = None

    if kline_df is not None and not kline_df.empty and "close" in kline_df.columns:
        closes = kline_df["close"].tolist()
        if len(closes) >= 60:
            # 最大回撤
            peak = closes[0]
            max_dd = 0.0
            for c in closes:
                if c > peak:
                    peak = c
                dd = (peak - c) / peak * 100
                if dd > max_dd:
                    max_dd = dd
            max_drawdown = round(max_dd, 1)

            # 日收益率波动率（年化）
            import math
            daily_returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            if daily_returns:
                mean_r = sum(daily_returns) / len(daily_returns)
                variance = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
                volatility = round(math.sqrt(variance * 252) * 100, 1)

            # 上涨天数比例
            up_days = sum(1 for r in daily_returns if r > 0)
            avg_up = round(up_days / len(daily_returns) * 100, 1) if daily_returns else None

            findings.append(f"历史最大回撤：{fmt_number(max_drawdown, 1)}%，年化波动率约 {fmt_number(volatility, 1)}%")
            findings.append(f"历史上涨概率：{pct_str(avg_up)}（近1年日均）")

            if max_drawdown < 30:
                score_cycle = 3.0
                findings.append("历史回撤控制在30%以内，走势稳健，规律性强")
            elif max_drawdown < 50:
                score_cycle = 2.5
                findings.append("历史回撤30%-50%，波动中等，需控制止损位")
            else:
                score_cycle = 1.5
                findings.append(f"⚠️ 历史回撤超过50%，高波动特征，操作风险大")
        else:
            findings.append("K线数据不足60日，历史规律统计受限")
    else:
        findings.append("⚠️ 历史K线数据获取失败，历史规律分析无法执行")

    # ── 历史上涨概率（4分）──
    score_win_rate = 2.0
    if avg_up is not None:
        if avg_up > 55:
            score_win_rate = 4.0
            findings.append(f"历史日胜率 {pct_str(avg_up)}（>55%），多头属性明显")
        elif avg_up > 50:
            score_win_rate = 3.0
            findings.append(f"历史日胜率 {pct_str(avg_up)}，略占多头优势")
        elif avg_up >= 45:
            score_win_rate = 2.0
            findings.append(f"历史日胜率 {pct_str(avg_up)}，多空均衡")
        else:
            score_win_rate = 1.5
            findings.append(f"历史日胜率 {pct_str(avg_up)}（<45%），偏空属性")

    # ── 波段套利空间（3分）──
    score_wave = 1.5
    if week52_position is not None:
        if week52_position < 20:
            score_wave = 3.0
            findings.append(f"52周位置 {week52_position:.1f}%（低位区间），历史赔率极高，波段布局价值强")
        elif week52_position < 40:
            score_wave = 2.5
            findings.append(f"52周位置 {week52_position:.1f}%（中低位），具备波段反弹空间")
        elif week52_position < 70:
            score_wave = 2.0
            findings.append(f"52周位置 {week52_position:.1f}%（中位区间），波段操作需谨慎止盈")
        else:
            score_wave = 1.0
            findings.append(f"⚠️ 52周位置 {week52_position:.1f}%（高位区间），追高风险大，历史赔率低")

    if week52_high and week52_low:
        findings.append(f"52周区间：{fmt_number(week52_low, 2)} ~ {fmt_number(week52_high, 2)}")

    total = score_cycle + score_win_rate + score_wave
    total = round(min(10.0, max(1.0, total)), 2)
    stars = score_to_stars(total)

    return ModuleResult(
        module_id="M13",
        module_name="历史走势规律与周期复盘",
        score=total,
        stars=stars,
        key_findings=findings[:5],
        short_advice=f"短线：{'52周低位，历史概率支持超跌反弹' if week52_position and week52_position < 20 else '高位追涨需严格止损' if week52_position and week52_position > 80 else '中位操作，参考均线支撑'}",
        mid_advice=f"中线：年化波动率约 {fmt_number(volatility, 1)}%，{'高波动需分批操作，控制单次仓位' if volatility and volatility > 60 else '波动适中，可正常配置'}",
        long_advice=f"长线：历史最大回撤 {fmt_number(max_drawdown, 1)}%，{'长线持有需做好承担相应回撤的心理准备' if max_drawdown and max_drawdown > 40 else '回撤可控，适合长线布局'}",
        conclusion=f"历史规律评分 {total:.1f}/10，52周位置 {fmt_number(week52_position, 1)}%，历史上涨概率 {pct_str(avg_up)}",
        detail={
            "week52_position": week52_position,
            "week52_high": week52_high,
            "week52_low": week52_low,
            "max_drawdown": max_drawdown,
            "avg_up": avg_up,
            "volatility": volatility,
        },
    )
