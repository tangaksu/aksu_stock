"""M06 多周期技术面实时操盘分析"""
from __future__ import annotations
from .base import ModuleResult, calc_trade_levels, fmt, score_to_stars


def _calc_ma(closes: list[float], n: int) -> float | None:
    if len(closes) < n:
        return None
    return round(sum(closes[-n:]) / n, 2)


def _calc_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for prev, current in zip(closes[-period - 1:-1], closes[-period:]):
        diff = current - prev
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _calc_macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    if len(closes) < slow + signal:
        return None, None, None

    def ema(data: list[float], n: int) -> list[float]:
        k = 2 / (n + 1)
        out = [data[0]]
        for value in data[1:]:
            out.append(value * k + out[-1] * (1 - k))
        return out

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    dif = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
    dea = ema(dif, signal)
    macd = [(d - e) * 2 for d, e in zip(dif[-len(dea):], dea)]
    return round(dif[-1], 4), round(dea[-1], 4), round(macd[-1], 4)


def _calc_kdj(highs: list[float], lows: list[float], closes: list[float], period: int = 9):
    if len(closes) < period or len(highs) < period or len(lows) < period:
        return None, None, None
    k = d = 50.0
    for idx in range(period - 1, len(closes)):
        period_high = max(highs[idx - period + 1:idx + 1])
        period_low = min(lows[idx - period + 1:idx + 1])
        if period_high == period_low:
            rsv = 50.0
        else:
            rsv = (closes[idx] - period_low) / (period_high - period_low) * 100
        k = k * 2 / 3 + rsv / 3
        d = d * 2 / 3 + k / 3
    j = 3 * k - 2 * d
    return round(k, 2), round(d, 2), round(j, 2)


def _sample_period(closes: list[float], step: int) -> list[float]:
    if not closes:
        return []
    start = (len(closes) - 1) % step
    sampled = [closes[idx] for idx in range(start, len(closes), step)]
    if sampled and sampled[-1] != closes[-1]:
        sampled.append(closes[-1])
    elif not sampled:
        sampled = closes[-1:]
    return sampled


def _trend_label(sampled: list[float], ma_period: int, fallback_label: str) -> str:
    if len(sampled) < max(ma_period, 2):
        return fallback_label
    ma_val = _calc_ma(sampled, ma_period)
    current = sampled[-1]
    prev = sampled[-2]
    if ma_val is None:
        return fallback_label
    if current > ma_val and current >= prev:
        return "多头上行"
    if current < ma_val and current <= prev:
        return "空头下行"
    return "震荡整理"


def _detect_pattern(closes: list[float]) -> str:
    if len(closes) < 40:
        return "样本不足，暂不识别形态"
    recent20 = closes[-20:]
    recent40 = closes[-40:]
    recent_high = max(recent20)
    recent_low = min(recent20)
    last = closes[-1]
    prev_high = max(recent40[:-5]) if len(recent40) > 5 else max(recent40)
    low_gap = abs(min(recent20[:10]) - min(recent20[10:])) / max(min(recent20[:10]), 1)
    if last >= prev_high * 0.995:
        return "平台整理后临近突破"
    if low_gap < 0.05 and last > sum(recent20[-5:]) / 5:
        return "双底雏形"
    if recent_high - recent_low <= recent_low * 0.12:
        return "箱体震荡"
    return "趋势延续"


def analyze_technical(data: dict) -> ModuleResult:
    rt = data.get("realtime") or {}
    df = data.get("kline_df")
    meta = (data.get("_meta") or {}).get("kline_df", {})

    findings: list[str] = []
    warnings: list[str] = []
    score = 5.0

    if df is None or df.empty:
        return ModuleResult(
            module_id="M06",
            module_name="多周期技术面实时操盘分析",
            score=5.0,
            stars=3,
            key_findings=[f"⚠️ K线数据获取失败：{meta.get('message', '无法完成技术分析')}"],
            conclusion="K线数据缺失，技术面分析已降级",
        )

    close_col = "收盘" if "收盘" in df.columns else "close"
    vol_col = "成交量" if "成交量" in df.columns else "volume"
    high_col = "最高" if "最高" in df.columns else "high"
    low_col = "最低" if "最低" in df.columns else "low"

    closes = [float(v) for v in df[close_col].tolist()]
    volumes = [float(v) for v in df[vol_col].tolist()] if vol_col in df.columns else []
    highs = [float(v) for v in df[high_col].tolist()] if high_col in df.columns else []
    lows = [float(v) for v in df[low_col].tolist()] if low_col in df.columns else []
    last = closes[-1] if closes else None
    if last is None:
        return ModuleResult(
            module_id="M06",
            module_name="多周期技术面实时操盘分析",
            score=5.0,
            stars=3,
            key_findings=["⚠️ 收盘价数据获取失败，技术面无法继续分析"],
            conclusion="收盘价缺失，技术面分析已降级",
        )

    ma5 = _calc_ma(closes, 5)
    ma10 = _calc_ma(closes, 10)
    ma20 = _calc_ma(closes, 20)
    ma60 = _calc_ma(closes, 60)
    ma120 = _calc_ma(closes, 120)
    findings.append(
        f"【技术面分析】（数据来源：{meta.get('source', 'K线数据')}，基于近{len(closes)}日K线）"
    )
    findings.append(f"均线：MA5={fmt(ma5)} MA10={fmt(ma10)} MA20={fmt(ma20)} MA60={fmt(ma60)} MA120={fmt(ma120)}")

    if all(v is not None for v in (ma5, ma10, ma20, ma60)):
        if last > ma5 > ma10 > ma20 > ma60:
            score += 2.0
            stance = "强势多头"
            findings.append("✅ 日线四线多头排列，趋势强势上攻")
        elif last > ma5 > ma20:
            score += 1.0
            stance = "中期上行"
            findings.append("✅ 日线短中期均线向上，趋势改善")
        elif last < ma5 < ma10 < ma20:
            score -= 2.0
            stance = "空头下行"
            warnings.append("🚨 日线四线空头排列，趋势偏弱")
        elif last < ma20:
            score -= 1.0
            stance = "弱势整理"
            warnings.append("⚠️ 当前价格跌破 MA20，中期趋势偏弱")
        else:
            stance = "震荡整理"
            findings.append("ℹ️ 日线均线缠绕，处于震荡整理区")
    else:
        stance = "数据不足"

    weekly_closes = _sample_period(closes, 5)
    monthly_closes = _sample_period(closes, 20)
    weekly_trend = _trend_label(weekly_closes, 5, "样本不足")
    monthly_trend = _trend_label(monthly_closes, 3, "样本不足")
    findings.append(f"多周期趋势：周线{weekly_trend} | 月线{monthly_trend}")
    if weekly_trend == "多头上行":
        score += 0.5
    elif weekly_trend == "空头下行":
        score -= 0.5
    if monthly_trend == "多头上行":
        score += 0.5
    elif monthly_trend == "空头下行":
        score -= 0.5

    rsi = _calc_rsi(closes, 14)
    if rsi is not None:
        findings.append(f"RSI(14)：{rsi:.1f}")
        if rsi > 80:
            score -= 1.0
            warnings.append(f"⚠️ RSI={rsi:.1f} 严重超买")
        elif rsi > 70:
            warnings.append(f"⚠️ RSI={rsi:.1f} 进入超买区")
        elif rsi < 20:
            score += 1.5
            findings.append(f"✅ RSI={rsi:.1f} 极度超卖，存在反弹机会")
        elif rsi < 30:
            score += 1.0
            findings.append(f"✅ RSI={rsi:.1f} 超卖区，关注企稳")

    dif, dea, macd_val = _calc_macd(closes)
    if dif is not None:
        findings.append(f"MACD：DIF={dif} DEA={dea} MACD柱={macd_val}")
        if dif > 0 and dea > 0 and macd_val > 0:
            score += 0.5
            findings.append("✅ MACD 位于零轴上方，趋势动能较强")
        elif macd_val and macd_val > 0 and dif > dea:
            score += 0.3
            findings.append("✅ MACD 金叉延续，多头动能占优")
        elif dif < 0 and dea < 0 and (macd_val or 0) < 0:
            score -= 0.5
            warnings.append("⚠️ MACD 死区运行，弱势格局")

    k_val = d_val = j_val = None
    if highs and lows and closes:
        k_val, d_val, j_val = _calc_kdj(highs, lows, closes)
        if k_val is not None:
            findings.append(f"KDJ：K={k_val} D={d_val} J={j_val}")
            if j_val is not None and j_val > 100:
                warnings.append("⚠️ KDJ J 值过高，短线过热")
                score -= 0.3
            elif j_val is not None and j_val < 0:
                findings.append("✅ KDJ J 值低于0，短线超卖")
                score += 0.3

    if volumes:
        avg_vol5 = sum(volumes[-5:]) / min(len(volumes), 5)
        avg_vol20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else avg_vol5
        vol_ratio = round(volumes[-1] / avg_vol20, 2) if avg_vol20 > 0 else 1.0
        findings.append(f"量比：{vol_ratio:.2f}（今日量 / 20日均量）")
        pct = rt.get("pct_change") or 0
        if vol_ratio > 2.0 and pct > 3:
            score += 1.0
            findings.append("✅ 放量上涨，量价配合强")
        elif vol_ratio > 1.5 and pct > 0:
            score += 0.5
            findings.append("✅ 温和放量上涨，资金配合较好")
        elif vol_ratio > 2.0 and pct < -3:
            score -= 1.0
            warnings.append("⚠️ 放量下跌，需警惕主力出货")
        elif vol_ratio < 0.5 and pct > 2:
            warnings.append("⚠️ 缩量上涨，动能持续性偏弱")
        if len(volumes) >= 20:
            recent10 = sum(volumes[-10:]) / 10
            prev10 = sum(volumes[-20:-10]) / 10
            if prev10 > 0:
                trend_pct = (recent10 - prev10) / prev10 * 100
                findings.append(f"近10日成交量变化：{trend_pct:+.0f}%")
                if trend_pct > 30:
                    score += 0.5
                    findings.append("✅ 近10日成交量显著扩张")
                elif trend_pct < -30:
                    score -= 0.3
                    warnings.append("⚠️ 近10日成交量明显萎缩")

    n_high = round(max(closes[-60:]), 2) if len(closes) >= 60 else round(max(closes), 2)
    n_low = round(min(closes[-60:]), 2) if len(closes) >= 60 else round(min(closes), 2)
    pos_pct = round((last - n_low) / (n_high - n_low) * 100, 1) if n_high > n_low else 50.0
    findings.append(f"60日定位：{pos_pct:.1f}%（低={n_low}，高={n_high}）")
    if pos_pct > 80:
        score -= 1.0
        warnings.append("⚠️ 价格位于60日高位区，追高风险较大")
    elif pos_pct < 20:
        score += 1.0
        findings.append("✅ 价格位于60日低位区，具备低位布局特征")

    support = round(min(closes[-20:]), 2) if len(closes) >= 20 else n_low
    resistance = round(max(closes[-20:]), 2) if len(closes) >= 20 else n_high
    pattern = _detect_pattern(closes)
    findings.append(f"支撑/压力：支撑位 {support} | 压力位 {resistance}")
    findings.append(f"技术形态：{pattern}")

    levels = calc_trade_levels(last, ma10, ma20)
    score = min(10.0, max(1.0, score))
    all_findings = findings + warnings
    conclusion = (
        f"技术面态势：{stance}，周线{weekly_trend}，月线{monthly_trend}。"
        f"操作位：入场{levels['entry_low']}-{levels['entry_high']}，止损{levels['stop_loss']}，"
        f"止盈{levels['take_profit_1']}/{levels['take_profit_2']}。"
    )

    return ModuleResult(
        module_id="M06",
        module_name="多周期技术面实时操盘分析",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=all_findings,
        short_advice=f"短线入场 {levels['entry_low']}-{levels['entry_high']}，止损 {levels['stop_loss']}，止盈 {levels['take_profit_1']}",
        mid_advice=f"中线以 MA20={fmt(ma20)} 和周线{weekly_trend}为多空分界，关注支撑 {support}",
        long_advice=f"长线以月线{monthly_trend}为主，突破压力位 {resistance} 后再提升仓位",
        conclusion=conclusion,
        detail={
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "ma60": ma60,
            "ma120": ma120,
            "rsi": rsi,
            "macd_dif": dif,
            "macd_dea": dea,
            "macd_bar": macd_val,
            "kdj_k": k_val,
            "kdj_d": d_val,
            "kdj_j": j_val,
            "weekly_trend": weekly_trend,
            "monthly_trend": monthly_trend,
            "support": support,
            "resistance": resistance,
            "pattern": pattern,
            "position_pct": pos_pct,
            "stance": stance,
            **levels,
        },
    )
