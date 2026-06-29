"""M13 历史走势规律与周期复盘"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars, fmt


def analyze_history(data: dict) -> ModuleResult:
    df = data.get("kline_df")
    rt = data.get("realtime") or {}

    findings = []
    score = 5.0

    if df is None or df.empty:
        return ModuleResult(
            module_id="M13",
            module_name="历史走势规律与周期复盘",
            score=5.0, stars=3,
            key_findings=["⚠️ 历史K线数据不可用"],
            conclusion="历史数据缺失，无法进行走势规律分析",
        )

    close_col = "收盘" if "收盘" in df.columns else "close"
    vol_col = "成交量" if "成交量" in df.columns else "volume"
    date_col = "日期" if "日期" in df.columns else df.columns[0]

    closes = df[close_col].tolist()
    dates = df[date_col].tolist() if date_col in df.columns else []
    vols = df[vol_col].tolist() if vol_col in df.columns else []

    current = closes[-1]

    # ── 历史区间统计 ──
    n1y = min(len(closes), 250)  # 近1年（约250个交易日）
    n6m = min(len(closes), 125)
    n3m = min(len(closes), 63)

    h1y = round(max(closes[-n1y:]), 2)
    l1y = round(min(closes[-n1y:]), 2)
    h6m = round(max(closes[-n6m:]), 2)
    l6m = round(min(closes[-n6m:]), 2)

    pos_1y = round((current - l1y) / (h1y - l1y) * 100, 1) if h1y > l1y else 50.0

    findings.append(f"近1年区间：{l1y} ~ {h1y}，当前位置：{pos_1y:.0f}%分位")
    findings.append(f"近6月区间：{l6m} ~ {h6m}")

    if pos_1y < 20:
        score += 2.0
        findings.append("✅ 处于年内低位区（<20%分位），历史底部布局窗口")
    elif pos_1y < 35:
        score += 1.0
        findings.append("✅ 处于年内偏低位（20-35%分位），有安全边际")
    elif pos_1y > 80:
        score -= 1.5
        findings.append("⚠️ 处于年内高位（>80%分位），追高风险较大")
    elif pos_1y > 65:
        score -= 0.5
        findings.append("⚠️ 处于年内偏高位（65-80%分位），上方压力较重")

    # ── 近期涨跌统计 ──
    if len(closes) >= 20:
        pct_3m = round((closes[-1] - closes[-n3m]) / closes[-n3m] * 100, 2)
        pct_6m = round((closes[-1] - closes[-n6m]) / closes[-n6m] * 100, 2)
        pct_1y = round((closes[-1] - closes[-n1y]) / closes[-n1y] * 100, 2)
        findings.append(f"近期涨跌：3月{pct_3m:+.1f}% | 6月{pct_6m:+.1f}% | 1年{pct_1y:+.1f}%")

        if pct_3m > 30:
            score -= 0.5
            findings.append("⚠️ 3个月内涨幅 > 30%，短期透支，回调风险较高")
        elif pct_3m < -30:
            score += 1.0
            findings.append("✅ 3个月跌幅 > 30%，超跌区域，反弹机会")

    # ── 波动率分析 ──
    if len(closes) >= 20:
        recent = closes[-20:]
        avg = sum(recent) / len(recent)
        variance = sum((c - avg) ** 2 for c in recent) / len(recent)
        std = variance ** 0.5
        volatility = round(std / avg * 100, 2)

        findings.append(f"20日波动率：{volatility:.1f}%")
        if volatility > 10:
            findings.append("⚠️ 波动率偏高，属高波动妖股，风控需严格")
        elif volatility < 2:
            score -= 0.3
            findings.append("ℹ️ 波动率极低，趋势性行情不明显")
        else:
            score += 0.3
            findings.append("✅ 波动率合理（2-10%），适合波段操作")

    # ── 最大回撤 ──
    if len(closes) >= 60:
        peak = closes[0]
        max_dd = 0.0
        for c in closes:
            if c > peak:
                peak = c
            dd = (peak - c) / peak * 100
            if dd > max_dd:
                max_dd = dd

        findings.append(f"历史最大回撤：{max_dd:.1f}%")
        if max_dd > 50:
            score -= 0.5
            findings.append("⚠️ 历史最大回撤超过50%，高风险属性")
        elif max_dd < 20:
            score += 0.5
            findings.append("✅ 历史最大回撤 < 20%，走势相对稳健")

    # ── 趋势性判断 ──
    if len(closes) >= 60:
        # 简单线性回归判断趋势
        n = 60
        x_vals = list(range(n))
        y_vals = closes[-n:]
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n
        num = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
        den = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
        slope = num / den if den else 0
        trend_pct = round(slope / y_mean * 100 * 250, 1)  # 年化趋势
        findings.append(f"60日价格趋势斜率（年化）：{trend_pct:+.1f}%")
        if trend_pct > 30:
            score += 1.0
            findings.append("✅ 上升趋势明确，价格中枢持续上移")
        elif trend_pct < -20:
            score -= 1.0
            findings.append("⚠️ 下降趋势明确，价格中枢持续下移")

    score = min(10.0, max(1.0, score))

    conclusion = (
        f"当前价格处于年内{pos_1y:.0f}%分位。"
        f"{'底部区域，历史低位布局机会' if pos_1y < 30 else '高位区域，追高需谨慎止损' if pos_1y > 70 else '中位震荡区，关注方向选择'}"
    )

    return ModuleResult(
        module_id="M13",
        module_name="历史走势规律与周期复盘",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice=f"年内{pos_1y:.0f}%分位，{'低位可短线博弹' if pos_1y < 30 else '高位减仓为主'}",
        mid_advice=f"{'中线处于低估历史区间，中期持仓价值显现' if pos_1y < 40 else '中线在高位区，波段做T降低成本'}",
        long_advice=f"历史低位布局（年内分位<20%）长线持有胜率更高",
        conclusion=conclusion,
        detail={"position_pct_1y": pos_1y, "h1y": h1y, "l1y": l1y},
    )
