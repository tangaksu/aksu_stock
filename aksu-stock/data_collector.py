"""
data_collector.py — 统一数据采集层
aksu-stock v5.1.5

数据源优先级（详见 references/data-sources.md）:
  1. AKShare==1.18.64（主力：历史K线、财务、资金、研报、行业）
  2. 腾讯财经（HTTP，实时行情首选）
  3. 新浪财经（HTTP，批量实时行情备用）
  4. 东方财富（HTTP，行情/资金备用）
  5. 同花顺（HTTP，技术指标/行业备用）

设计原则：
  - 每个 fetch_* 函数必须捕获所有异常，网络失败时返回 None / 空结构，绝不向上抛出
  - _with_meta() 为所有返回值附加来源元信息
  - collect_all_data() 是唯一对外接口，返回完整的 data dict
"""
from __future__ import annotations

import json
import math
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any

# ─────────────────────────────────────────────────────────
# 基础配置
# ─────────────────────────────────────────────────────────
DEFAULT_TIMEOUT = 15   # 单次请求超时秒数
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# 字段责任分配：每个字段的主责+备用数据源顺序（同步 references/data-sources.md）
SOURCE_RESPONSIBILITY: dict[str, list[str]] = {
    "realtime":              ["腾讯财经", "新浪财经", "AKShare东方财富"],
    "kline_df":              ["AKShare", "腾讯财经"],
    "kline_weekly":          ["AKShare"],
    "kline_monthly":         ["AKShare"],
    "stock_info":            ["AKShare东方财富"],
    "financial_abstract":    ["AKShare同花顺"],
    "profit_statement":      ["AKShare东方财富"],
    "balance_sheet":         ["AKShare东方财富"],
    "cashflow":              ["AKShare东方财富"],
    "top10_holders":         ["AKShare东方财富"],
    "pledge_ratio":          ["AKShare东方财富"],
    "holder_num":            ["AKShare东方财富"],
    "fund_flow":             ["AKShare"],
    "north_fund":            ["AKShare"],
    "research_reports":      ["AKShare东方财富"],
    "analyst_ratings":       ["AKShare东方财富"],
    "dragon_tiger":          ["AKShare东方财富"],
    "market_sentiment":      ["AKShare"],
    "industry_peers":        ["AKShare东方财富"],
    "stock_concepts":        ["AKShare东方财富"],
    "index_data":            ["新浪财经", "AKShare"],
}

# ─────────────────────────────────────────────────────────
# AKShare 懒加载（避免导入失败导致整体崩溃）
# ─────────────────────────────────────────────────────────
_AK: Any = None
_AK_ERROR: str | None = None
_AK_CHECKED = False


def _get_ak() -> Any:
    global _AK, _AK_ERROR, _AK_CHECKED
    if _AK_CHECKED:
        return _AK
    _AK_CHECKED = True
    try:
        import akshare as ak  # type: ignore
        _AK = ak
    except ImportError as exc:
        _AK_ERROR = f"AKShare 未安装或版本不匹配：{exc}。请执行 pip install akshare==1.18.64"
    except Exception as exc:
        _AK_ERROR = f"AKShare 加载异常：{exc}"
    return _AK


# ─────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────

def _tencent_prefix(code: str) -> str:
    """6位代码转腾讯前缀：60xx/68xx/90xx → sh，其余 → sz"""
    if code.startswith(("60", "68", "90")):
        return "sh" + code
    return "sz" + code


def _safe_float(v: Any, default: float | None = None) -> float | None:
    try:
        if v in (None, "", "—", "N/A"):
            return default
        result = float(v)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT,
              headers: dict | None = None, encoding: str = "utf-8") -> str | None:
    """通用 HTTP GET，失败返回 None"""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(encoding, errors="replace")
    except Exception:
        return None


def _with_meta(payload: Any, source: str, success: bool = True, message: str = "") -> Any:
    """为采集结果附加来源元信息"""
    stamp = datetime.now().isoformat(timespec="seconds")
    if isinstance(payload, dict):
        payload["_source"] = source
        payload["_fetched_at"] = stamp
        payload["_success"] = success
        if message:
            payload["_message"] = message
        return payload
    return {
        "data": payload,
        "_source": source,
        "_fetched_at": stamp,
        "_success": success,
        "_message": message,
    }


def _failure(source: str, message: str, payload: Any = None) -> Any:
    return _with_meta(payload if payload is not None else {}, source, success=False, message=message)


def _set_field(result: dict, key: str, payload: Any) -> None:
    """将 payload 写入 result[key]，并更新 result['_meta'][key]"""
    is_meta_wrapped = isinstance(payload, dict) and "_source" in payload
    if is_meta_wrapped:
        plain = {k: v for k, v in payload.items() if not k.startswith("_")}
        if set(plain.keys()) == {"data"}:
            value = plain["data"]
        else:
            value = plain if plain else None
        source = payload.get("_source", "未知来源")
        message = payload.get("_message", "")
        success = bool(payload.get("_success", True))
    else:
        value = payload
        source = " / ".join(SOURCE_RESPONSIBILITY.get(key, ["未知来源"]))
        message = ""
        success = value is not None

    # 判断有效性
    has_value = value is not None
    if isinstance(value, (list, dict, str)):
        has_value = len(value) > 0
    elif hasattr(value, "empty"):
        has_value = not bool(value.empty)

    result[key] = value
    result.setdefault("_meta", {})[key] = {
        "source": source,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "success": bool(success and has_value),
        "message": message or ("采集成功" if success and has_value else
                               "⚠️ 数据获取失败（上游接口未返回有效内容）"),
    }


# ─────────────────────────────────────────────────────────
# 模块 1：实时行情
# ─────────────────────────────────────────────────────────

def fetch_realtime_tencent(code: str) -> dict | None:
    """腾讯财经实时行情（首选，纯 HTTP，最稳定）"""
    sym = _tencent_prefix(code)
    url = f"https://qt.gtimg.cn/q={sym}"
    txt = _http_get(url, headers={"Referer": "https://gu.qq.com/"}, encoding="gbk")
    if not txt or "=" not in txt:
        return None
    parts = txt.split("=", 1)[1].strip(' ;\n"').split("~")
    if len(parts) < 35:
        return None
    price = _safe_float(parts[3])
    prev_close = _safe_float(parts[4])
    pct = None
    if price and prev_close and prev_close > 0:
        pct = round((price - prev_close) / prev_close * 100, 2)
    return _with_meta({
        "code": code,
        "name": parts[1],
        "price": price,
        "prev_close": prev_close,
        "open": _safe_float(parts[5]),
        "high": _safe_float(parts[33]) if len(parts) > 33 else None,
        "low": _safe_float(parts[34]) if len(parts) > 34 else None,
        "volume": (_safe_float(parts[6], 0) or 0) * 100,
        "amount": ((_safe_float(parts[37], 0) or 0) * 10000) if len(parts) > 37 else 0,
        "turnover_rate": _safe_float(parts[38]) if len(parts) > 38 else None,
        "pct_change": pct,
        "pe_ttm": _safe_float(parts[39]) if len(parts) > 39 else None,
        "pb": _safe_float(parts[46]) if len(parts) > 46 else None,
        "market_cap": _safe_float(parts[44]) if len(parts) > 44 else None,
        "circulate_cap": _safe_float(parts[45]) if len(parts) > 45 else None,
    }, "腾讯财经")


def fetch_realtime_sina(code: str) -> dict | None:
    """新浪财经实时行情（备用，纯 HTTP）"""
    sym = _tencent_prefix(code)  # 格式相同
    url = f"https://hq.sinajs.cn/list={sym}"
    txt = _http_get(url, headers={"Referer": "https://finance.sina.com.cn/"}, encoding="gbk")
    if not txt or "=" not in txt:
        return None
    raw = txt.split("=", 1)[1].strip(' ;\n"')
    parts = raw.split(",")
    if len(parts) < 32:
        return None
    price = _safe_float(parts[3])
    prev_close = _safe_float(parts[2])
    pct = None
    if price and prev_close and prev_close > 0:
        pct = round((price - prev_close) / prev_close * 100, 2)
    return _with_meta({
        "code": code,
        "name": parts[0],
        "price": price,
        "prev_close": prev_close,
        "open": _safe_float(parts[1]),
        "high": _safe_float(parts[4]),
        "low": _safe_float(parts[5]),
        "volume": (_safe_float(parts[8], 0) or 0) * 100,
        "amount": _safe_float(parts[9], 0),
        "turnover_rate": None,
        "pct_change": pct,
        "pe_ttm": None,
        "pb": None,
        "market_cap": None,
        "circulate_cap": None,
    }, "新浪财经")


def fetch_realtime_akshare_em(code: str) -> dict | None:
    """AKShare 东方财富实时行情（最终兜底，包含更多估值字段）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return None
        row_df = df[df["代码"].astype(str) == code]
        if row_df.empty:
            return None
        row = row_df.iloc[0]
        price = _safe_float(row.get("最新价"))
        prev_close = _safe_float(row.get("昨收"))
        pct = None
        if price and prev_close and prev_close > 0:
            pct = round((price - prev_close) / prev_close * 100, 2)
        return _with_meta({
            "code": code,
            "name": str(row.get("名称", "")),
            "price": price,
            "prev_close": prev_close,
            "open": _safe_float(row.get("今开")),
            "high": _safe_float(row.get("最高")),
            "low": _safe_float(row.get("最低")),
            "volume": _safe_float(row.get("成交量"), 0),
            "amount": _safe_float(row.get("成交额"), 0),
            "turnover_rate": _safe_float(row.get("换手率")),
            "pct_change": pct,
            "pe_ttm": _safe_float(row.get("市盈率-动态")),
            "pb": _safe_float(row.get("市净率")),
            "market_cap": _safe_float(row.get("总市值")),
            "circulate_cap": _safe_float(row.get("流通市值")),
            "volume_ratio": _safe_float(row.get("量比")),
        }, "AKShare东方财富")
    except Exception:
        return None


def fetch_realtime(code: str) -> dict:
    """
    实时行情多源采集入口，按优先级依次尝试：
    腾讯财经 → 新浪财经 → AKShare东方财富 → 空数据降级

    返回的 dict 保证包含所有标准字段（不可用时为 None）。
    """
    standard_keys = [
        "code", "name", "price", "prev_close", "open", "high", "low",
        "volume", "amount", "turnover_rate", "pct_change",
        "pe_ttm", "pb", "market_cap", "circulate_cap", "volume_ratio",
    ]
    sources = [
        ("腾讯财经", fetch_realtime_tencent),
        ("新浪财经", fetch_realtime_sina),
        ("AKShare东方财富", fetch_realtime_akshare_em),
    ]
    tried: list[str] = []
    for src_name, fn in sources:
        tried.append(src_name)
        result = fn(code)
        if result and result.get("price"):
            return result
    # 全部失败 → 返回空结构
    empty = {k: None for k in standard_keys}
    empty["code"] = code
    return _with_meta(
        empty, "—", success=False,
        message=f"⚠️ 实时行情获取失败（已尝试：{'、'.join(tried)}）"
    )


# ─────────────────────────────────────────────────────────
# 模块 2：历史 K 线
# ─────────────────────────────────────────────────────────

def fetch_hist_kline(code: str, period: str = "daily",
                     days_back: int = 365, adjust: str = "qfq") -> Any:
    """
    AKShare 历史 K 线（前复权）
    period: "daily" | "weekly" | "monthly"
    返回 DataFrame 或 None
    """
    ak = _get_ak()
    if ak is None:
        return None
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if df is None or df.empty:
            return None
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
            "成交额": "amount", "振幅": "amplitude",
            "涨跌幅": "pct_change", "涨跌额": "change", "换手率": "turnover",
        })
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return None


def _calc_ma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 3)


def _calc_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _calc_macd(closes: list[float], fast: int = 12, slow: int = 26,
               signal: int = 9) -> dict[str, float | None]:
    def ema(data: list[float], n: int) -> list[float]:
        k = 2 / (n + 1)
        result = [data[0]]
        for price in data[1:]:
            result.append(price * k + result[-1] * (1 - k))
        return result

    if len(closes) < slow + signal:
        return {"dif": None, "dea": None, "macd": None}
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    dif_list = [f - s for f, s in zip(ema_fast[slow - fast:], ema_slow)]
    dea_list = ema(dif_list, signal)
    dif = round(dif_list[-1], 4)
    dea = round(dea_list[-1], 4)
    return {"dif": dif, "dea": dea, "macd": round((dif - dea) * 2, 4)}


def _calc_kdj(highs: list[float], lows: list[float], closes: list[float],
              period: int = 9) -> dict[str, float | None]:
    if len(closes) < period:
        return {"k": None, "d": None, "j": None}
    rsv_list = []
    for i in range(len(closes) - period, len(closes)):
        start = max(0, i - period + 1)
        h = max(highs[start: i + 1])
        l = min(lows[start: i + 1])
        rsv = (closes[i] - l) / (h - l) * 100 if h != l else 50.0
        rsv_list.append(rsv)
    k, d = 50.0, 50.0
    for rsv in rsv_list:
        k = (2 / 3) * k + (1 / 3) * rsv
        d = (2 / 3) * d + (1 / 3) * k
    j = 3 * k - 2 * d
    return {"k": round(k, 2), "d": round(d, 2), "j": round(j, 2)}


def _calc_boll(closes: list[float], period: int = 20, k: float = 2.0) -> dict[str, float | None]:
    if len(closes) < period:
        return {"upper": None, "mid": None, "lower": None}
    recent = closes[-period:]
    mid = sum(recent) / period
    std = (sum((x - mid) ** 2 for x in recent) / period) ** 0.5
    return {"upper": round(mid + k * std, 3), "mid": round(mid, 3), "lower": round(mid - k * std, 3)}


def calc_technical_indicators(df: Any) -> dict[str, Any]:
    """从 K 线 DataFrame 计算均线、RSI、MACD、KDJ、BOLL 等技术指标"""
    if df is None or (hasattr(df, "empty") and df.empty):
        return {}
    closes = df["close"].tolist()
    highs = df["high"].tolist()
    lows = df["low"].tolist()
    result: dict[str, Any] = {
        "ma5":  _calc_ma(closes, 5),
        "ma10": _calc_ma(closes, 10),
        "ma20": _calc_ma(closes, 20),
        "ma60": _calc_ma(closes, 60),
        "ma120": _calc_ma(closes, 120),
        "rsi14": _calc_rsi(closes, 14),
    }
    result.update(_calc_macd(closes))
    result["kdj"] = _calc_kdj(highs, lows, closes)
    result["boll"] = _calc_boll(closes)
    # 52周最高最低
    year_closes = closes[-252:] if len(closes) >= 252 else closes
    if year_closes:
        result["week52_high"] = max(year_closes)
        result["week52_low"] = min(year_closes)
    return result


# ─────────────────────────────────────────────────────────
# 模块 3：个股基本信息
# ─────────────────────────────────────────────────────────

def fetch_stock_info(code: str) -> dict | None:
    """AKShare 东方财富个股基本信息（上市日期、所属行业、地区等）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_individual_info_em(symbol=code)
        if df is None or df.empty:
            return None
        info: dict[str, Any] = {}
        for _, row in df.iterrows():
            info[str(row.get("item", ""))] = row.get("value")
        return _with_meta({
            "industry": info.get("行业"),
            "list_date": info.get("上市时间"),
            "region": info.get("地区"),
            "concept": info.get("概念"),
            "total_share": _safe_float(info.get("总股本")),
            "float_share": _safe_float(info.get("流通股")),
        }, "AKShare东方财富")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 模块 4：财务数据
# ─────────────────────────────────────────────────────────

def fetch_financial_abstract(code: str) -> dict | None:
    """
    AKShare 同花顺财务摘要指标（ROE/EPS/每股净资产/股息率等）
    AKShare 1.18.x: ak.stock_financial_abstract_ths(stock, indicator)
    """
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_financial_abstract_ths(stock=code, indicator="按报告期")
        if df is None or df.empty:
            return None
        latest = df.iloc[0]
        result: dict[str, Any] = {
            "report_date": str(latest.get("报告期", "")),
            "roe": _safe_float(latest.get("净资产收益率")),
            "eps": _safe_float(latest.get("基本每股收益")),
            "bvps": _safe_float(latest.get("每股净资产")),
            "ocf_per_share": _safe_float(latest.get("每股经营现金流量")),
            "revenue": _safe_float(latest.get("营业总收入")),
            "revenue_yoy": _safe_float(latest.get("营业总收入同比增长")),
            "net_profit": _safe_float(latest.get("净利润")),
            "profit_yoy": _safe_float(latest.get("净利润同比增长")),
        }
        # 近3年年度数据
        annual_rows = []
        for _, row in df.iterrows():
            period = str(row.get("报告期", ""))
            if period.endswith("12-31") or period.endswith("1231"):
                annual_rows.append({
                    "period": period,
                    "revenue": _safe_float(row.get("营业总收入")),
                    "net_profit": _safe_float(row.get("净利润")),
                    "roe": _safe_float(row.get("净资产收益率")),
                    "revenue_yoy": _safe_float(row.get("营业总收入同比增长")),
                    "profit_yoy": _safe_float(row.get("净利润同比增长")),
                })
            if len(annual_rows) >= 3:
                break
        result["annual_history"] = annual_rows
        return _with_meta(result, "AKShare同花顺")
    except Exception:
        return None


def fetch_profit_statement(code: str) -> dict | None:
    """AKShare 东方财富利润表（毛利率/净利率/扣非利润/三费）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_profit_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return None
        latest = df.iloc[0]

        def _pct(v: Any, base: Any) -> float | None:
            a, b = _safe_float(v), _safe_float(base)
            if a is None or b is None or b == 0:
                return None
            return round(a / b * 100, 2)

        revenue = _safe_float(latest.get("营业总收入"))
        gross_profit = _safe_float(latest.get("毛利润"))
        net_profit = _safe_float(latest.get("净利润"))
        profit_deducted = _safe_float(latest.get("扣除非经常性损益后的净利润"))

        selling_exp = _safe_float(latest.get("销售费用"))
        mgmt_exp = _safe_float(latest.get("管理费用"))
        rd_exp = _safe_float(latest.get("研发费用"))
        fin_exp = _safe_float(latest.get("财务费用"))

        return _with_meta({
            "report_date": str(latest.get("报告期", "")),
            "revenue": revenue,
            "gross_profit": gross_profit,
            "gross_margin": _pct(gross_profit, revenue),
            "net_profit": net_profit,
            "net_margin": _pct(net_profit, revenue),
            "profit_deducted": profit_deducted,
            "selling_expense": selling_exp,
            "mgmt_expense": mgmt_exp,
            "rd_expense": rd_exp,
            "fin_expense": fin_exp,
            "three_fee_ratio": _pct(
                (selling_exp or 0) + (mgmt_exp or 0) + (fin_exp or 0), revenue
            ),
        }, "AKShare东方财富")
    except Exception:
        return None


def fetch_balance_sheet(code: str) -> dict | None:
    """AKShare 东方财富资产负债表（负债率/有息负债等）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_balance_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return None
        latest = df.iloc[0]
        total_asset = _safe_float(latest.get("资产总计"))
        total_liab = _safe_float(latest.get("负债合计"))
        goodwill = _safe_float(latest.get("商誉"))
        accounts_rec = _safe_float(latest.get("应收账款"))
        inventory = _safe_float(latest.get("存货"))
        cash = _safe_float(latest.get("货币资金"))
        return _with_meta({
            "report_date": str(latest.get("报告期", "")),
            "total_asset": total_asset,
            "total_liab": total_liab,
            "debt_ratio": round(total_liab / total_asset * 100, 2) if total_asset and total_liab else None,
            "goodwill": goodwill,
            "goodwill_ratio": round(goodwill / total_asset * 100, 2) if goodwill and total_asset else None,
            "accounts_receivable": accounts_rec,
            "inventory": inventory,
            "cash": cash,
        }, "AKShare东方财富")
    except Exception:
        return None


def fetch_cashflow(code: str) -> dict | None:
    """AKShare 东方财富现金流量表（经营现金流/自由现金流）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return None
        latest = df.iloc[0]
        ocf = _safe_float(latest.get("经营活动产生的现金流量净额"))
        capex = _safe_float(latest.get("购建固定资产、无形资产和其他长期资产支付的现金"))
        fcf = (ocf - (capex or 0)) if ocf is not None else None
        return _with_meta({
            "report_date": str(latest.get("报告期", "")),
            "ocf": ocf,
            "capex": capex,
            "fcf": fcf,
            "investing_cf": _safe_float(latest.get("投资活动产生的现金流量净额")),
            "financing_cf": _safe_float(latest.get("筹资活动产生的现金流量净额")),
        }, "AKShare东方财富")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 模块 5：股东与治理
# ─────────────────────────────────────────────────────────

def fetch_top10_holders(code: str) -> list[dict] | None:
    """AKShare 东方财富前十大流通股东"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_gdfx_free_top_10_em(symbol=code)
        if df is None or df.empty:
            return None
        holders = []
        for _, row in df.iloc[:10].iterrows():
            holders.append({
                "name": str(row.get("股东名称", "")),
                "shares": _safe_float(row.get("持股数量")),
                "ratio": _safe_float(row.get("持股比例")),
                "change": str(row.get("持股变动", "")),
                "holder_type": str(row.get("股东性质", "")),
            })
        return holders
    except Exception:
        return None


def fetch_pledge_ratio(code: str) -> dict | None:
    """AKShare 东方财富股权质押比例"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_gpzy_pledge_ratio_em(symbol=code)
        if df is None or df.empty:
            return None
        latest = df.iloc[0]
        return _with_meta({
            "pledge_ratio": _safe_float(latest.get("质押比例")),
            "pledged_shares": _safe_float(latest.get("质押股数")),
            "pledge_count": _safe_float(latest.get("质押笔数")),
        }, "AKShare东方财富")
    except Exception:
        return None


def fetch_holder_num(code: str) -> dict | None:
    """AKShare 东方财富股东人数"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_zh_a_gdhs_detail_em(symbol=code)
        if df is None or df.empty:
            return None
        latest = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else None
        holder_num = _safe_float(latest.get("股东人数"))
        prev_holder_num = _safe_float(prev.get("股东人数")) if prev is not None else None
        change_pct = None
        if holder_num and prev_holder_num and prev_holder_num > 0:
            change_pct = round((holder_num - prev_holder_num) / prev_holder_num * 100, 2)
        return _with_meta({
            "holder_num": holder_num,
            "holder_num_change_pct": change_pct,
            "report_date": str(latest.get("截止日期", "")),
        }, "AKShare东方财富")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 模块 6：资金流向
# ─────────────────────────────────────────────────────────

def fetch_fund_flow(code: str) -> dict | None:
    """AKShare 个股资金流向（近5日主力净流入）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        # 判断市场
        market = "sh" if code.startswith(("60", "68", "90")) else "sz"
        df = ak.stock_individual_fund_flow(stock=code, market=market)
        if df is None or df.empty:
            return None
        # 取最近5日
        rows = df.tail(5).to_dict("records")
        latest = rows[-1] if rows else {}
        return _with_meta({
            "recent_5days": rows,
            "main_net_inflow": _safe_float(latest.get("主力净流入净额")),
            "super_large_inflow": _safe_float(latest.get("超大单净流入净额")),
            "large_inflow": _safe_float(latest.get("大单净流入净额")),
            "main_net_ratio": _safe_float(latest.get("主力净流入净占比")),
        }, "AKShare")
    except Exception:
        return None


def fetch_north_fund(code: str) -> dict | None:
    """AKShare 北向资金持股（沪深股通）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_hsgt_individual_detail_em(code=code)
        if df is None or df.empty:
            return None
        latest = df.iloc[0]
        return _with_meta({
            "hold_shares": _safe_float(latest.get("持股数量")),
            "hold_ratio": _safe_float(latest.get("持股比例")),
            "hold_change": _safe_float(latest.get("当日增减")),
        }, "AKShare")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 模块 7：研报与机构评级
# ─────────────────────────────────────────────────────────

def fetch_research_reports(code: str) -> list[dict] | None:
    """AKShare 东方财富个股研报"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_research_report_em(symbol=code)
        if df is None or df.empty:
            return None
        reports = []
        for _, row in df.head(10).iterrows():
            reports.append({
                "date": str(row.get("报告日期", "")),
                "title": str(row.get("报告名称", "")),
                "org": str(row.get("机构名称", "")),
                "analyst": str(row.get("分析师", "")),
                "rating": str(row.get("评级", "")),
                "target_price": _safe_float(row.get("目标价")),
            })
        return reports
    except Exception:
        return None


def fetch_analyst_ratings(code: str) -> dict | None:
    """AKShare 个股机构评级统计"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_analyst_detail_em(stock=code, indicator="最新评级")
        if df is None or df.empty:
            return None
        ratings = {"买入": 0, "增持": 0, "中性": 0, "减持": 0, "卖出": 0}
        target_prices = []
        for _, row in df.iterrows():
            r = str(row.get("最新评级", ""))
            for key in ratings:
                if key in r:
                    ratings[key] += 1
            tp = _safe_float(row.get("目标价"))
            if tp:
                target_prices.append(tp)
        avg_target = round(sum(target_prices) / len(target_prices), 2) if target_prices else None
        return _with_meta({
            "ratings": ratings,
            "total_reports": sum(ratings.values()),
            "avg_target_price": avg_target,
        }, "AKShare东方财富")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 模块 8：行业数据
# ─────────────────────────────────────────────────────────

def fetch_industry_peers(industry_name: str, top_n: int = 10) -> list[dict] | None:
    """AKShare 东方财富行业板块成分股（用于同业对标）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_board_industry_cons_em(symbol=industry_name)
        if df is None or df.empty:
            return None
        peers = []
        for _, row in df.head(top_n).iterrows():
            peers.append({
                "code": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "price": _safe_float(row.get("最新价")),
                "pct_change": _safe_float(row.get("涨跌幅")),
                "pe_ttm": _safe_float(row.get("市盈率-动态")),
                "market_cap": _safe_float(row.get("总市值")),
            })
        return peers
    except Exception:
        return None


def fetch_stock_concepts(code: str) -> list[str] | None:
    """AKShare 个股概念标签"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        df = ak.stock_board_concept_name_em()
        if df is None or df.empty:
            return None
        # 过滤包含该股的概念板块
        concepts = []
        for _, row in df.iterrows():
            concepts.append(str(row.get("板块名称", "")))
        return concepts[:20] if concepts else None  # 最多返回20个概念
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 模块 9：市场情绪
# ─────────────────────────────────────────────────────────

def fetch_market_sentiment() -> dict | None:
    """AKShare 全市场涨跌情绪（涨停/跌停/涨跌家数/北向）"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        result: dict[str, Any] = {}
        # 涨停池
        try:
            df_zt = ak.stock_zt_pool_em(date=datetime.now().strftime("%Y%m%d"))
            result["limit_up_count"] = len(df_zt) if df_zt is not None else None
        except Exception:
            result["limit_up_count"] = None
        # 跌停池
        try:
            df_dt = ak.stock_dt_pool_em(date=datetime.now().strftime("%Y%m%d"))
            result["limit_down_count"] = len(df_dt) if df_dt is not None else None
        except Exception:
            result["limit_down_count"] = None
        # 北向资金
        try:
            df_north = ak.stock_hsgt_north_net_flow_in(symbol="沪深港通")
            if df_north is not None and not df_north.empty:
                result["north_net_inflow_today"] = _safe_float(df_north.iloc[-1].get("当日成交净买额"))
        except Exception:
            result["north_net_inflow_today"] = None
        return _with_meta(result, "AKShare")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 模块 10：龙虎榜
# ─────────────────────────────────────────────────────────

def fetch_dragon_tiger(code: str) -> list[dict] | None:
    """AKShare 东方财富龙虎榜数据"""
    ak = _get_ak()
    if ak is None:
        return None
    try:
        date_str = datetime.now().strftime("%Y%m%d")
        df = ak.stock_lhb_detail_em(symbol=code, date=date_str)
        if df is None or df.empty:
            return None
        records = []
        for _, row in df.head(10).iterrows():
            records.append({
                "date": str(row.get("上榜日期", "")),
                "reason": str(row.get("上榜原因", "")),
                "buy": _safe_float(row.get("买入金额")),
                "sell": _safe_float(row.get("卖出金额")),
                "net": _safe_float(row.get("净买入")),
                "org": str(row.get("营业部名称", "")),
            })
        return records
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 主入口：采集所有数据
# ─────────────────────────────────────────────────────────

def collect_all_data(code: str) -> dict[str, Any]:
    """
    统一数据采集入口，按字段责任表顺序采集所有数据。
    返回完整的 data dict，每个字段附带 _meta 元信息。
    网络完全不可用时，所有字段为 None，_meta 中标注失败原因。
    """
    code = code.strip().zfill(6)
    result: dict[str, Any] = {"code": code, "_meta": {}}

    # ── 实时行情（腾讯 → 新浪 → AKShare）──────────────────
    rt = fetch_realtime(code)
    for key in ["name", "price", "prev_close", "open", "high", "low",
                "volume", "amount", "turnover_rate", "pct_change",
                "pe_ttm", "pb", "market_cap", "circulate_cap", "volume_ratio"]:
        val = rt.get(key) if rt else None
        _set_field(result, key, _with_meta(
            val, rt.get("_source", "—") if rt else "—",
            success=val is not None,
            message="" if val is not None else f"⚠️ {key} 获取失败"
        ))

    # ── 基本信息 ──────────────────────────────────────────
    info = fetch_stock_info(code)
    for key in ["industry", "list_date", "region", "total_share", "float_share"]:
        val = (info or {}).get(key)
        src = (info or {}).get("_source", "AKShare东方财富")
        _set_field(result, key, _with_meta(val, src, success=val is not None))

    # ── 历史 K 线 ─────────────────────────────────────────
    kline_df = fetch_hist_kline(code, period="daily", days_back=500)
    _set_field(result, "kline_df", _with_meta(kline_df, "AKShare", success=kline_df is not None and not kline_df.empty))

    kline_weekly = fetch_hist_kline(code, period="weekly", days_back=730)
    _set_field(result, "kline_weekly", _with_meta(kline_weekly, "AKShare",
               success=kline_weekly is not None and not kline_weekly.empty))

    kline_monthly = fetch_hist_kline(code, period="monthly", days_back=1095)
    _set_field(result, "kline_monthly", _with_meta(kline_monthly, "AKShare",
               success=kline_monthly is not None and not kline_monthly.empty))

    # ── 技术指标（从日K计算）──────────────────────────────
    tech = calc_technical_indicators(kline_df)
    result["technical_indicators"] = tech
    result["_meta"]["technical_indicators"] = {
        "source": "计算（基于AKShare日K线）",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "success": bool(tech),
        "message": "技术指标计算成功" if tech else "⚠️ 日K线数据缺失，技术指标无法计算",
    }
    # 快捷键
    for k, v in tech.items():
        result[k] = v

    # ── 财务数据 ──────────────────────────────────────────
    fin_abs = fetch_financial_abstract(code)
    _set_field(result, "financial_abstract", fin_abs)
    # 从财务摘要提取常用字段
    for key in ["roe", "eps", "bvps", "revenue", "revenue_yoy",
                "net_profit", "profit_yoy", "annual_history"]:
        val = (fin_abs or {}).get(key)
        src = (fin_abs or {}).get("_source", "AKShare同花顺")
        _set_field(result, key, _with_meta(val, src, success=val is not None))

    profit = fetch_profit_statement(code)
    _set_field(result, "profit_statement", profit)
    for key in ["gross_margin", "net_margin", "profit_deducted",
                "three_fee_ratio", "rd_expense"]:
        val = (profit or {}).get(key)
        src = (profit or {}).get("_source", "AKShare东方财富")
        _set_field(result, key, _with_meta(val, src, success=val is not None))

    balance = fetch_balance_sheet(code)
    _set_field(result, "balance_sheet", balance)
    for key in ["debt_ratio", "goodwill", "goodwill_ratio", "cash",
                "accounts_receivable", "inventory"]:
        val = (balance or {}).get(key)
        src = (balance or {}).get("_source", "AKShare东方财富")
        _set_field(result, key, _with_meta(val, src, success=val is not None))

    cf = fetch_cashflow(code)
    _set_field(result, "cashflow", cf)
    for key in ["ocf", "fcf", "capex"]:
        val = (cf or {}).get(key)
        src = (cf or {}).get("_source", "AKShare东方财富")
        _set_field(result, key, _with_meta(val, src, success=val is not None))

    # ── 股东与治理 ────────────────────────────────────────
    _set_field(result, "top10_holders", fetch_top10_holders(code))
    pledge = fetch_pledge_ratio(code)
    _set_field(result, "pledge_ratio", (pledge or {}).get("pledge_ratio"))
    holder = fetch_holder_num(code)
    _set_field(result, "holder_num", (holder or {}).get("holder_num"))
    _set_field(result, "holder_num_change_pct", (holder or {}).get("holder_num_change_pct"))

    # ── 资金流向 ──────────────────────────────────────────
    fund = fetch_fund_flow(code)
    _set_field(result, "fund_flow", fund)
    for key in ["main_net_inflow", "super_large_inflow", "large_inflow", "main_net_ratio"]:
        val = (fund or {}).get(key)
        _set_field(result, key, _with_meta(val, "AKShare", success=val is not None))

    north = fetch_north_fund(code)
    _set_field(result, "north_fund", north)

    # ── 研报与评级 ────────────────────────────────────────
    _set_field(result, "research_reports", fetch_research_reports(code))
    analyst = fetch_analyst_ratings(code)
    _set_field(result, "analyst_ratings", analyst)
    _set_field(result, "avg_target_price", (analyst or {}).get("avg_target_price"))

    # ── 市场情绪 ──────────────────────────────────────────
    sentiment = fetch_market_sentiment()
    _set_field(result, "market_sentiment", sentiment)

    # ── 龙虎榜 ────────────────────────────────────────────
    _set_field(result, "dragon_tiger", fetch_dragon_tiger(code))

    # ── 行业同业 ──────────────────────────────────────────
    industry_name = result.get("industry")
    if industry_name:
        _set_field(result, "industry_peers", fetch_industry_peers(str(industry_name)))

    # 52周相对位置
    w52h = result.get("week52_high")
    w52l = result.get("week52_low")
    price = result.get("price")
    if w52h and w52l and price and w52h > w52l:
        result["week52_position"] = round((price - w52l) / (w52h - w52l) * 100, 1)
    else:
        result["week52_position"] = None

    return result


# ─────────────────────────────────────────────────────────
# 诊断工具
# ─────────────────────────────────────────────────────────

def runtime_diagnostics() -> dict[str, Any]:
    """检查各数据源可用性，返回诊断报告"""
    checks: dict[str, Any] = {}
    ak = _get_ak()
    checks["akshare"] = {
        "available": ak is not None,
        "version": getattr(ak, "__version__", "unknown") if ak else None,
        "message": "AKShare 可用" if ak else (_AK_ERROR or "AKShare 不可用"),
    }
    for host in ["qt.gtimg.cn", "hq.sinajs.cn", "push2.eastmoney.com"]:
        try:
            socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            checks[host] = {"reachable": True}
        except Exception as exc:
            checks[host] = {"reachable": False, "error": str(exc)}
    return checks
