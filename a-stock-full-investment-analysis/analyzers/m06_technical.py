"""M06 多周期技术面实时操盘分析"""
from __future__ import annotations
import math
from .base import ModuleResult, score_to_stars, fmt, pct_fmt


def _calc_ma(closes: list, n: int) -> float | None:
    if len(closes) < n:
        return None
    return round(sum(closes[-n:]) / n, 2)


def _calc_rsi(closes: list, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-period + i - 1] - closes[-period + i - 2] if i > 1 else closes[-period] - closes[-period - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _calc_macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9):
    if len(closes) < slow + signal:
        return None, None, None

    def ema(data, n):
        k = 2 / (n + 1)
        result = [data[0]]
        for v in data[1:]:
            result.append(v * k + result[-1] * (1 - k))
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    dif = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
    dea = ema(dif, signal)
    macd = [(d - e) * 2 for d, e in zip(dif[-len(dea):], dea)]
    return round(dif[-1], 4), round(dea[-1], 4), round(macd[-1], 4)


def analyze_technical(data: dict) -> ModuleResult:
    rt = data.get("realtime") or {}
    df = data.get("kline_df")

    findings = []
    warnings = []
    score = 5.0

    if df is None or df.empty:
        return ModuleResult(
            module_id="M06",
            module_name="多周期技术面实时操盘分析",
            score=5.0, stars=3,
            key_findings=["⚠️ K线数据获取失败，技术面分析不可用"],
            conclusion="K线数据缺失，无法进行技术分析",
        )

    # 标准化列名
    close_col = "收盘" if "收盘" in df.columns else "close"
    vol_col = "成交量" if "成交量" in df.columns else "volume"
    high_col = "最高" if "最高" in df.columns else "high"
    low_col = "最低" if "最低" in df.columns else "low"

    closes = df[close_col].tolist()
    volumes = df[vol_col].tolist() if vol_col in df.columns else []
    highs = df[high_col].tolist() if high_col in df.columns else []
    lows = df[low_col].tolist() if low_col in df.columns else []

    last = closes[-1] if closes else None
    if not last:
        return ModuleResult(
            module_id="M06", module_name="多周期技术面实时操盘分析",
            score=5.0, stars=3,
            key_findings=["⚠️ 收盘价数据缺失"],
            conclusion="数据不足，无法分析",
        )

    # ── 均线系统 ──
    ma5 = _calc_ma(closes, 5)
    ma10 = _calc_ma(closes, 10)
    ma20 = _calc_ma(closes, 20)
    ma30 = _calc_ma(closes, 30)
    ma60 = _calc_ma(closes, 60)
    ma120 = _calc_ma(closes, 120)

    findings.append(
        f"均线：MA5={fmt(ma5)} MA10={fmt(ma10)} MA20={fmt(ma20)} "
        f"MA60={fmt(ma60)} MA120={fmt(ma120)}"
    )

    # 多头/空头排列判断
    if ma5 and ma10 and ma20 and ma60:
        if last > ma5 > ma10 > ma20 > ma60:
            score += 2.0
            findings.append("✅ 四线多头排列（日线），强势上攻态势")
            stance = "强势多头"
        elif last > ma5 and ma5 > ma20:
            score += 1.0
            findings.append("✅ 短期均线多头，中期趋势向上")
            stance = "中期上行"
        elif last < ma5 < ma10 < ma20:
            score -= 2.0
            warnings.append("🚨 四线空头排列，趋势向下，规避持仓")
            stance = "空头下行"
        elif last < ma20:
            score -= 1.0
            findings.append("⚠️ 价格跌破MA20，中期趋势偏弱")
            stance = "弱势整理"
        else:
            stance = "震荡整理"
            findings.append("ℹ️ 均线系统混乱，处于震荡格局")
    else:
        stance = "数据不足"

    # ── RSI ──
    rsi = _calc_rsi(closes, 14)
    if rsi is not None:
        findings.append(f"RSI(14)：{rsi:.1f}")
        if rsi > 80:
            score -= 1.0
            warnings.append(f"⚠️ RSI={rsi:.1f} 严重超买，注意高位风险")
        elif rsi > 70:
            warnings.append(f"⚠️ RSI={rsi:.1f} 超买区，短线可适当减仓")
        elif rsi < 20:
            score += 1.5
            findings.append(f"✅ RSI={rsi:.1f} 极度超卖，短线反弹机会")
        elif rsi < 30:
            score += 1.0
            findings.append(f"✅ RSI={rsi:.1f} 超卖区，短线关注反弹")

    # ── MACD ──
    dif, dea, macd_val = _calc_macd(closes)
    if dif is not None:
        findings.append(f"MACD: DIF={dif} DEA={dea} MACD柱={macd_val}")
        if dif > 0 and dea > 0 and macd_val > 0:
            score += 0.5
            findings.append("✅ MACD 金区（DIF/DEA均>0，柱>0），多头动能强")
        elif macd_val and macd_val > 0 and (dif or 0) > (dea or 0):
            score += 0.3
            findings.append("✅ MACD 金叉（DIF上穿DEA），买入信号")
        elif dif and dea and dif < 0 and dea < 0 and (macd_val or 0) < 0:
            score -= 0.5
            findings.append("⚠️ MACD 死区（DIF/DEA均<0），弱势格局")

    # ── 量价分析 ──
    if volumes:
        avg_vol5 = sum(volumes[-5:]) / 5
        avg_vol20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else avg_vol5
        vol_ratio = round(volumes[-1] / avg_vol20, 2) if avg_vol20 > 0 else 1.0
        findings.append(f"量比：{vol_ratio:.2f}（今日量 / 20日均量）")

        pct = rt.get("pct_change") or 0
        if vol_ratio > 2.0 and pct > 3:
            score += 1.0
            findings.append("✅ 涨停级放量拉升，主力资金介入明显")
        elif vol_ratio > 1.5 and pct > 0:
            score += 0.5
            findings.append("✅ 放量上涨，量价配合良好")
        elif vol_ratio > 2.0 and pct < -3:
            score -= 1.0
            warnings.append("⚠️ 放量大跌，主力出货信号")
        elif vol_ratio < 0.5 and pct > 2:
            findings.append("⚠️ 缩量上涨，动能不足，可持续性存疑")

        # ── 成交量趋势（近10日 vs 前10日均量对比）──
        if len(volumes) >= 20:
            vol_recent10 = sum(volumes[-10:]) / 10
            vol_prev10 = sum(volumes[-20:-10]) / 10
            if vol_prev10 > 0:
                vol_trend_pct = (vol_recent10 - vol_prev10) / vol_prev10 * 100
                if vol_trend_pct > 30:
                    score += 0.5
                    findings.append(f"✅ 近10日均量较前10日放大 {vol_trend_pct:.0f}%，成交量持续扩张，资金活跃度提升")
                elif vol_trend_pct < -30:
                    findings.append(f"⚠️ 近10日均量较前10日萎缩 {abs(vol_trend_pct):.0f}%，成交量持续萎缩，市场热情降温")
                else:
                    findings.append(f"ℹ️ 成交量趋势平稳（近10日均量变化 {vol_trend_pct:+.0f}%）")

    # ── 关键位 ──
    n_high = round(max(closes[-60:]), 2) if len(closes) >= 60 else round(max(closes), 2)
    n_low = round(min(closes[-60:]), 2) if len(closes) >= 60 else round(min(closes), 2)
    pos_pct = round((last - n_low) / (n_high - n_low) * 100, 1) if n_high > n_low else 50.0

    findings.append(f"60日区间：低 {n_low} ~ 高 {n_high}（当前位置：{pos_pct:.0f}%）")

    if pos_pct > 80:
        warnings.append(f"⚠️ 价格处于60日高位（{pos_pct:.0f}%），追高需谨慎")
    elif pos_pct < 20:
        score += 1.0
        findings.append(f"✅ 价格处于60日低位（{pos_pct:.0f}%），底部区域")

    score = min(10.0, max(1.0, score))

    # ── 操作位 ──
    stop_loss = round(ma20, 2) if ma20 else round(last * 0.92, 2)
    entry_zone_low = round(ma10 or last * 0.98, 2)
    entry_zone_high = round(last * 1.02, 2)
    take_profit_1 = round(last * 1.08, 2)
    take_profit_2 = round(last * 1.15, 2)

    all_findings = findings + warnings
    conclusion = (
        f"技术面态势：{stance}。"
        f"建议入场区间：{entry_zone_low}-{entry_zone_high}，"
        f"止损位：{stop_loss}（MA20），"
        f"止盈目标：{take_profit_1}（+8%）/ {take_profit_2}（+15%）。"
    )

    return ModuleResult(
        module_id="M06",
        module_name="多周期技术面实时操盘分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice=f"短线入场区间 {entry_zone_low}-{entry_zone_high}，止损 {stop_loss}，止盈 {take_profit_1}",
        mid_advice=f"MA20（{fmt(ma20)}）为中线多空分界，站稳则持有，跌破则减仓",
        long_advice=f"月线{'多头' if ma120 and last > ma120 else '空头'}格局，{'长线可持有' if ma120 and last > ma120 else '长线等待月线趋势扭转'}",
        conclusion=conclusion,
        detail={
            "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
            "rsi": rsi, "macd_dif": dif, "macd_dea": dea,
            "stop_loss": stop_loss, "entry_low": entry_zone_low,
            "take_profit_1": take_profit_1, "take_profit_2": take_profit_2,
            "position_pct": pos_pct, "stance": stance,
        },
    )
