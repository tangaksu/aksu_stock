"""
统一数据采集层 — 覆盖实时行情、历史K线、财务数据、资金流向、行业信息、机构评级。

数据源优先级:
  1. 腾讯财经（实时行情，最稳定）
  2. 新浪财经（批量实时行情）
  3. AKShare — 东方财富 / 同花顺接口（财务、资金、研报等）
  4. 腾讯历史K线（AKShare超时时备用）
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta
from typing import Any

# ──────────────────────────────────────────────
# 基础配置
# ──────────────────────────────────────────────
DEFAULT_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _tencent_prefix(code: str) -> str:
    """6位代码转腾讯前缀: 60xx/68xx/90xx → sh，其余 → sz"""
    if code.startswith(("60", "68", "90")):
        return "sh" + code
    return "sz" + code


def _safe_float(v: Any, default: float | None = None) -> float | None:
    try:
        if v in (None, "", "0", "0.00"):
            return default
        result = float(v)
        import math
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


# ──────────────────────────────────────────────
# 模块 1：实时行情
# ──────────────────────────────────────────────

def fetch_realtime_tencent(code: str) -> dict | None:
    """腾讯财经实时行情（单只，首选）"""
    sym = _tencent_prefix(code)
    url = f"https://qt.gtimg.cn/q={sym}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://gu.qq.com/",
        })
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            txt = resp.read().decode("gbk", errors="replace")
        if "=" not in txt:
            return None
        parts = txt.split("=", 1)[1].strip(' ;\n"').split("~")
        if len(parts) < 35:
            return None
        price = _safe_float(parts[3])
        prev_close = _safe_float(parts[4])
        pct = None
        if price and prev_close and prev_close > 0:
            pct = round((price - prev_close) / prev_close * 100, 2)
        return {
            "code": code,
            "name": parts[1],
            "price": price,
            "prev_close": prev_close,
            "open": _safe_float(parts[5]),
            "high": _safe_float(parts[33]),
            "low": _safe_float(parts[34]),
            "volume": _safe_float(parts[6], 0) * 100 if parts[6] else 0,
            "amount": _safe_float(parts[37], 0) * 10000 if len(parts) > 37 else 0,
            "turnover_rate": _safe_float(parts[38]) if len(parts) > 38 else None,
            "pct_change": pct,
            "pe_ttm": _safe_float(parts[39]) if len(parts) > 39 else None,
            "pb": _safe_float(parts[46]) if len(parts) > 46 else None,
            "market_cap": _safe_float(parts[44]) if len(parts) > 44 else None,
            "circulate_cap": _safe_float(parts[45]) if len(parts) > 45 else None,
        }
    except Exception:
        return None


def fetch_realtime_sina_batch(codes: list[str]) -> dict[str, dict]:
    """新浪财经批量实时行情"""
    if not codes:
        return {}
    syms = [_tencent_prefix(c) for c in codes]
    url = "https://hq.sinajs.cn/list=" + ",".join(syms)
    out: dict[str, dict] = {}
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://finance.sina.com.cn/",
        })
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            txt = resp.read().decode("gbk", errors="replace")
        for line in txt.strip().split("\n"):
            if "=" not in line:
                continue
            head, body = line.split("=", 1)
            sym = head.split("_")[-1]
            code = sym[2:]
            parts = body.strip(' ;\n"').split(",")
            if len(parts) < 32:
                continue
            price = _safe_float(parts[3])
            prev_close = _safe_float(parts[2])
            pct = None
            if price and prev_close and prev_close > 0:
                pct = round((price - prev_close) / prev_close * 100, 2)
            out[code] = {
                "code": code,
                "name": parts[0],
                "open": _safe_float(parts[1]),
                "prev_close": prev_close,
                "price": price,
                "high": _safe_float(parts[4]),
                "low": _safe_float(parts[5]),
                "volume": _safe_float(parts[8], 0),
                "amount": _safe_float(parts[9], 0),
                "pct_change": pct,
            }
    except Exception:
        pass
    return out


def fetch_realtime(codes: list[str]) -> dict[str, dict]:
    """统一实时行情入口：新浪批量 + 腾讯逐个补全"""
    out = fetch_realtime_sina_batch(codes)
    for c in codes:
        if c not in out or not out[c].get("price"):
            q = fetch_realtime_tencent(c)
            if q:
                out[c] = q
    return out


# ──────────────────────────────────────────────
# 模块 2：历史 K 线
# ──────────────────────────────────────────────

def fetch_hist_kline(code: str, days_back: int = 250, adjust: str = "qfq"):
    """历史K线：AKShare首选，腾讯备用"""
    try:
        import akshare as ak
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start, end_date=end, adjust=adjust,
        )
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    # 腾讯备用
    sym = _tencent_prefix(code)
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={sym},day,,,{days_back},{adjust}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        kdata = (
            data.get("data", {}).get(sym, {}).get("qfqday")
            or data.get("data", {}).get(sym, {}).get("day")
            or []
        )
        if not kdata:
            return None
        import pandas as pd
        rows = []
        for r in kdata:
            try:
                rows.append({
                    "日期": r[0], "开盘": float(r[1]), "收盘": float(r[2]),
                    "最高": float(r[3]), "最低": float(r[4]),
                    "成交量": float(r[5]) if len(r) > 5 else 0,
                })
            except Exception:
                continue
        return pd.DataFrame(rows) if rows else None
    except Exception:
        return None


# ──────────────────────────────────────────────
# 模块 3：财务数据（AKShare）
# ──────────────────────────────────────────────

def fetch_financial_indicator(code: str) -> dict | None:
    """主要财务指标（ROE、毛利率、净利率等）"""
    try:
        import akshare as ak
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2020")
        if df is None or df.empty:
            return None
        row = df.iloc[-1].to_dict()
        return {
            "report_date": str(df.index[-1]) if hasattr(df.index[-1], "__str__") else "",
            "roe": _safe_float(row.get("净资产收益率(%)")),
            "gross_margin": _safe_float(row.get("销售毛利率(%)")),
            "net_margin": _safe_float(row.get("销售净利率(%)")),
            "debt_ratio": _safe_float(row.get("资产负债率(%)")),
            "current_ratio": _safe_float(row.get("流动比率")),
            "quick_ratio": _safe_float(row.get("速动比率")),
            "ar_turnover": _safe_float(row.get("应收账款周转率(次)")),
            "inv_turnover": _safe_float(row.get("存货周转率(次)")),
            "eps": _safe_float(row.get("基本每股收益(元)")),
        }
    except Exception:
        return None


def fetch_profit_statement(code: str) -> list[dict]:
    """利润表数据（近12季，约3年）"""
    try:
        import akshare as ak
        df = ak.stock_profit_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.head(12).iterrows():
            result.append({
                "period": str(row.get("REPORT_DATE", "")),
                "revenue": _safe_float(row.get("TOTAL_OPERATE_INCOME")),
                "net_profit": _safe_float(row.get("PARENT_NETPROFIT")),
                "deducted_profit": _safe_float(row.get("DEDUCT_PARENT_NETPROFIT")),
                "gross_profit": _safe_float(row.get("GROSS_PROFIT")),
                "revenue_yoy": _safe_float(row.get("TOTAL_OPERATE_INCOME_YOY")),
                "profit_yoy": _safe_float(row.get("PARENT_NETPROFIT_YOY")),
                "rd_expense": _safe_float(row.get("RESEARCH_EXPENSE")),
            })
        return result
    except Exception:
        return []


def fetch_balance_sheet(code: str) -> dict | None:
    """资产负债表关键项"""
    try:
        import akshare as ak
        df = ak.stock_balance_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return None
        row = df.iloc[0].to_dict()
        return {
            "total_assets": _safe_float(row.get("TOTAL_ASSETS")),
            "total_liab": _safe_float(row.get("TOTAL_LIABILITIES")),
            "equity": _safe_float(row.get("TOTAL_EQUITY")),
            "cash": _safe_float(row.get("MONETARYFUNDS")),
            "goodwill": _safe_float(row.get("GOODWILL")),
            "receivables": _safe_float(row.get("ACCOUNTS_RECE")),
            "inventory": _safe_float(row.get("INVENTORY")),
            "interest_bearing_debt": _safe_float(row.get("INTEREST_PAYABLE")),
        }
    except Exception:
        return None


def fetch_cashflow(code: str) -> dict | None:
    """现金流量表"""
    try:
        import akshare as ak
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=code)
        if df is None or df.empty:
            return None
        row = df.iloc[0].to_dict()
        return {
            "operating_cf": _safe_float(row.get("NETCASH_OPERATE")),
            "investing_cf": _safe_float(row.get("NETCASH_INVEST")),
            "financing_cf": _safe_float(row.get("NETCASH_FINANCE")),
            "free_cf": _safe_float(row.get("FREE_CASHFLOW")),
            "capex": _safe_float(row.get("CONSTRUCT_LONG_ASSET")),
        }
    except Exception:
        return None


def fetch_annual_financial(code: str) -> list[dict]:
    """年度财务摘要（近3年：营收、净利润、毛利率、研发投入）"""
    try:
        import akshare as ak
        df = ak.stock_profit_sheet_by_yearly_em(symbol=code)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.head(4).iterrows():
            revenue = _safe_float(row.get("TOTAL_OPERATE_INCOME"))
            gross_profit = _safe_float(row.get("GROSS_PROFIT"))
            gross_margin = None
            if revenue and gross_profit and revenue > 0:
                gross_margin = round(gross_profit / revenue * 100, 2)
            result.append({
                "year": str(row.get("REPORT_DATE", ""))[:4],
                "revenue": revenue,
                "net_profit": _safe_float(row.get("PARENT_NETPROFIT")),
                "gross_profit": gross_profit,
                "gross_margin": gross_margin,
                "rd_expense": _safe_float(row.get("RESEARCH_EXPENSE")),
                "revenue_yoy": _safe_float(row.get("TOTAL_OPERATE_INCOME_YOY")),
                "profit_yoy": _safe_float(row.get("PARENT_NETPROFIT_YOY")),
            })
        return result
    except Exception:
        return []


# ──────────────────────────────────────────────
# 模块 4：股东与治理数据
# ──────────────────────────────────────────────

def fetch_top10_holders(code: str) -> list[dict]:
    """前十大流通股东"""
    try:
        import akshare as ak
        df = ak.stock_circulate_stockholder_details(symbol=code)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.head(10).iterrows():
            result.append({
                "name": str(row.get("股东名称", "")),
                "ratio": _safe_float(row.get("持股比例")),
                "shares": _safe_float(row.get("持股数量")),
                "change": str(row.get("增减", "")),
            })
        return result
    except Exception:
        return []


def fetch_pledge_ratio(code: str) -> dict | None:
    """股权质押情况"""
    try:
        import akshare as ak
        df = ak.stock_pledge_stat_em(symbol=code)
        if df is None or df.empty:
            return None
        row = df.iloc[-1].to_dict()
        return {
            "pledge_ratio": _safe_float(row.get("质押比例(%)")),
            "pledge_shares": _safe_float(row.get("质押股数(股)")),
            "pledge_times": int(row.get("质押次数", 0) or 0),
        }
    except Exception:
        return None


def fetch_holder_num(code: str) -> dict | None:
    """股东人数变化（判断筹码集中度）"""
    try:
        import akshare as ak
        df = ak.stock_holder_num_em(symbol=code)
        if df is None or df.empty:
            return None
        rows = df.head(4).to_dict("records")
        h_num = int(rows[0].get("股东人数", 0) or 0)
        holder_num_prev = int(rows[1].get("股东人数", 0) or 0) if len(rows) > 1 else None
        # 安全计算股东人数变化比例，避免除零
        if holder_num_prev and holder_num_prev > 0:
            h_change_pct = round((h_num - holder_num_prev) / holder_num_prev * 100, 2)
        else:
            h_change_pct = None
        return {
            "latest_date": str(rows[0].get("截止日期", "")),
            "holder_num": h_num,
            "holder_num_prev": holder_num_prev,
            "holder_num_change_pct": h_change_pct,
        }
    except Exception:
        return None


def fetch_management_changes(code: str) -> list[dict]:
    """高管增减持"""
    try:
        import akshare as ak
        df = ak.stock_em_hold_change_detail(symbol=code)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.head(10).iterrows():
            result.append({
                "name": str(row.get("姓名", "")),
                "position": str(row.get("职位", "")),
                "change_type": str(row.get("变动方式", "")),
                "shares": _safe_float(row.get("变动股数")),
                "price": _safe_float(row.get("均价")),
                "date": str(row.get("变动完成日期", "")),
            })
        return result
    except Exception:
        return []


# ──────────────────────────────────────────────
# 模块 5：行业与市场数据
# ──────────────────────────────────────────────

def fetch_stock_info(code: str) -> dict | None:
    """个股基本信息（行业、上市日期、主营业务等）"""
    try:
        import akshare as ak
        df = ak.stock_individual_info_em(symbol=code)
        if df is None or df.empty:
            return None
        info = {}
        for _, row in df.iterrows():
            k = str(row.get("item", ""))
            v = str(row.get("value", ""))
            info[k] = v
        # 兼容不同字段名（沪深主板 vs 科创/创业板）
        industry = (
            info.get("行业")
            or info.get("所属行业")
            or info.get("所在行业")
            or info.get("申万行业")
            or ""
        )
        return {
            "name": info.get("股票简称", ""),
            "code": info.get("股票代码", code),
            "industry": industry,
            "list_date": info.get("上市时间", ""),
            "total_shares": info.get("总股本", ""),
            "float_shares": info.get("流通股", ""),
            "market_cap": info.get("总市值", ""),
            "float_cap": info.get("流通市值", ""),
            "pe_ttm": info.get("市盈率(动)", ""),
            "pb": info.get("市净率", ""),
            "board": info.get("所属板块", ""),
            "business": info.get("主营业务", ""),
        }
    except Exception:
        return None


def fetch_industry_rank(industry: str) -> list[dict]:
    """同行业股票排名（按涨跌幅）"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_cons_em(symbol=industry)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.head(20).iterrows():
            result.append({
                "code": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "price": _safe_float(row.get("最新价")),
                "pct": _safe_float(row.get("涨跌幅")),
                "pe": _safe_float(row.get("市盈率(动)")),
                "pb": _safe_float(row.get("市净率")),
                "market_cap": _safe_float(row.get("总市值")),
            })
        return result
    except Exception:
        return []


def fetch_sector_fund_flow(code: str) -> dict | None:
    """个股资金流向（主力净流入，近30日）"""
    try:
        import akshare as ak
        df = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith(("6", "9")) else "sz")
        if df is None or df.empty:
            return None
        rows = df.head(30).to_dict("records")
        latest = rows[0] if rows else {}
        return {
            "date": str(latest.get("日期", "")),
            "main_net": _safe_float(latest.get("主力净流入-净额")),
            "main_net_pct": _safe_float(latest.get("主力净流入-净占比")),
            "super_big_net": _safe_float(latest.get("超大单净流入-净额")),
            "big_net": _safe_float(latest.get("大单净流入-净额")),
            "medium_net": _safe_float(latest.get("中单净流入-净额")),
            "small_net": _safe_float(latest.get("小单净流入-净额")),
            "recent": rows[:30],
        }
    except Exception:
        return None


def fetch_north_fund_flow() -> dict | None:
    """北向资金当日净流入"""
    try:
        import akshare as ak
        df = ak.stock_em_hsgt_north_net_flow_in(symbol="沪股通")
        if df is None or df.empty:
            return None
        latest = df.iloc[-1].to_dict()
        return {
            "date": str(latest.get("日期", "")),
            "sh_net": _safe_float(latest.get("当日净流入")),
        }
    except Exception:
        return None


# ──────────────────────────────────────────────
# 模块 6：估值历史分位
# ──────────────────────────────────────────────

def fetch_valuation_history(code: str) -> dict | None:
    """历史PE/PB分位（近3年）"""
    try:
        import akshare as ak
        df = ak.stock_a_indicator_lg(symbol=code)
        if df is None or df.empty:
            return None
        df_sorted = df.sort_values("trade_date")
        pe_vals = df_sorted["pe"].dropna().tolist()
        pb_vals = df_sorted["pb"].dropna().tolist()
        if not pe_vals:
            return None
        current_pe = pe_vals[-1]
        current_pb = pb_vals[-1] if pb_vals else None
        pe_sorted = sorted(pe_vals)
        # 用二分搜索确定当前PE在历史序列中的分位数
        import bisect
        idx = bisect.bisect_left(pe_sorted, current_pe)
        pe_pct = round(idx / len(pe_sorted) * 100, 1)
        pb_pct = None
        if pb_vals:
            pb_sorted = sorted(pb_vals)
            import bisect
            pb_idx = bisect.bisect_left(pb_sorted, current_pb)
            pb_pct = round(pb_idx / len(pb_sorted) * 100, 1)
        return {
            "current_pe": round(current_pe, 2),
            "pe_min": round(min(pe_vals), 2),
            "pe_max": round(max(pe_vals), 2),
            "pe_avg": round(sum(pe_vals) / len(pe_vals), 2),
            "pe_percentile": pe_pct,
            "current_pb": round(current_pb, 2) if current_pb else None,
            "pb_percentile": pb_pct,
        }
    except Exception:
        return None


# ──────────────────────────────────────────────
# 模块 7：龙虎榜与机构研报
# ──────────────────────────────────────────────

def fetch_dragon_tiger(code: str) -> list[dict]:
    """龙虎榜数据（近30天）"""
    try:
        import akshare as ak
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        df = ak.stock_lhb_stock_statistic_em(symbol=code, start_date=start, end_date=end)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.head(5).iterrows():
            result.append({
                "date": str(row.get("上榜日期", "")),
                "reason": str(row.get("上榜原因", "")),
                "buy_total": _safe_float(row.get("买方合计金额")),
                "sell_total": _safe_float(row.get("卖方合计金额")),
                "net": _safe_float(row.get("净额")),
            })
        return result
    except Exception:
        return []


def fetch_research_reports(code: str) -> list[dict]:
    """机构研报（近6个月）"""
    try:
        import akshare as ak
        df = ak.stock_research_report_em(symbol=code)
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.head(10).iterrows():
            result.append({
                "date": str(row.get("发布日期", "")),
                "title": str(row.get("报告名称", "")),
                "institution": str(row.get("研究机构", "")),
                "rating": str(row.get("投资评级", "")),
                "target_price": _safe_float(row.get("目标价格")),
            })
        return result
    except Exception:
        return []


def fetch_analyst_consensus(code: str) -> dict | None:
    """分析师一致预期"""
    try:
        import akshare as ak
        df = ak.stock_analyst_forecast_em(symbol=code)
        if df is None or df.empty:
            return None
        buy = 0
        hold = 0
        sell = 0
        target_prices = []
        for _, row in df.iterrows():
            rating = str(row.get("投资评级", ""))
            tp = _safe_float(row.get("目标价格"))
            if tp:
                target_prices.append(tp)
            if "买入" in rating or "增持" in rating or "推荐" in rating:
                buy += 1
            elif "中性" in rating or "持有" in rating:
                hold += 1
            elif "减持" in rating or "卖出" in rating:
                sell += 1
        total = buy + hold + sell
        return {
            "buy": buy,
            "hold": hold,
            "sell": sell,
            "total": total,
            "buy_ratio": round(buy / total * 100, 1) if total else 0,
            "avg_target": round(sum(target_prices) / len(target_prices), 2) if target_prices else None,
            "max_target": round(max(target_prices), 2) if target_prices else None,
            "min_target": round(min(target_prices), 2) if target_prices else None,
        }
    except Exception:
        return None


# ──────────────────────────────────────────────
# 模块 8：市场情绪与连板数据
# ──────────────────────────────────────────────

def fetch_limit_up_pool() -> dict | None:
    """今日涨停池统计"""
    try:
        import akshare as ak
        date_str = datetime.now().strftime("%Y%m%d")
        df = ak.stock_zt_pool_em(date=date_str)
        if df is None or df.empty:
            return None
        return {
            "date": date_str,
            "count": len(df),
            "top_consecutive": int(df["连板数"].max() if "连板数" in df.columns else 0),
        }
    except Exception:
        return None


def fetch_market_sentiment() -> dict | None:
    """大盘情绪（涨跌家数、涨停跌停）"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return None
        up = len(df[df["涨跌幅"] > 0]) if "涨跌幅" in df.columns else None
        down = len(df[df["涨跌幅"] < 0]) if "涨跌幅" in df.columns else None
        limit_up = len(df[df["涨跌幅"] >= 9.9]) if "涨跌幅" in df.columns else None
        limit_down = len(df[df["涨跌幅"] <= -9.9]) if "涨跌幅" in df.columns else None
        return {
            "up_count": up,
            "down_count": down,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "mood_score": round(up / (up + down) * 100, 1) if up and down else None,
        }
    except Exception:
        return None


# ──────────────────────────────────────────────
# 模块 9：大盘指数
# ──────────────────────────────────────────────

def fetch_index_data() -> dict | None:
    """主要指数实时行情（上证、深成、创业板）"""
    indices = {
        "sh000001": "上证指数",
        "sz399001": "深成指",
        "sz399006": "创业板指",
        "sh000300": "沪深300",
    }
    codes = list(indices.keys())
    result = {}
    try:
        req = urllib.request.Request(
            "https://hq.sinajs.cn/list=" + ",".join(codes),
            headers={"User-Agent": USER_AGENT, "Referer": "https://finance.sina.com.cn/"},
        )
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            txt = resp.read().decode("gbk", errors="replace")
        for line in txt.strip().split("\n"):
            if "=" not in line:
                continue
            head, body = line.split("=", 1)
            sym = head.strip().split("_")[-1]
            parts = body.strip(' ;\n"').split(",")
            if len(parts) < 10:
                continue
            price = _safe_float(parts[3])
            prev = _safe_float(parts[2])
            pct = round((price - prev) / prev * 100, 2) if price and prev and prev > 0 else None
            name = indices.get(sym, sym)
            result[name] = {"price": price, "pct_change": pct, "amount": _safe_float(parts[9])}
    except Exception:
        pass
    return result if result else None


# ──────────────────────────────────────────────
# 模块 10：个股概念与板块
# ──────────────────────────────────────────────

def fetch_stock_concept(code: str) -> list[str]:
    """个股所属概念板块"""
    try:
        import akshare as ak
        df = ak.stock_board_concept_name_em()
        if df is None or df.empty:
            return []
        concepts = []
        for _, row in df.iterrows():
            board_code = str(row.get("代码", ""))
            try:
                members = ak.stock_board_concept_cons_em(symbol=str(row.get("板块名称", "")))
                if members is not None and not members.empty:
                    if code in members["代码"].astype(str).values:
                        concepts.append(str(row.get("板块名称", "")))
                        if len(concepts) >= 5:
                            break
            except Exception:
                continue
        return concepts
    except Exception:
        return []


# ──────────────────────────────────────────────
# 统一数据采集入口
# ──────────────────────────────────────────────

def collect_all_data(code: str) -> dict:
    """
    统一采集所有分析所需数据，返回结构化数据字典。
    每个子模块独立容错，任一失败不影响整体。
    """
    result: dict[str, Any] = {"code": code, "fetch_time": datetime.now().isoformat()}

    # 1. 实时行情
    print(f"  [1/10] 采集实时行情...", end="", flush=True)
    rt_map = fetch_realtime([code])
    result["realtime"] = rt_map.get(code)
    print("✓")

    # 2. 历史K线（250个交易日）
    print(f"  [2/10] 采集历史K线...", end="", flush=True)
    df = fetch_hist_kline(code, days_back=365)
    result["kline_df"] = df
    print("✓" if df is not None else "⚠ 失败")

    # 3. 个股基本信息
    print(f"  [3/10] 采集基本信息...", end="", flush=True)
    result["stock_info"] = fetch_stock_info(code)
    print("✓" if result["stock_info"] else "⚠ 失败")

    # 4. 财务指标
    print(f"  [4/10] 采集财务指标...", end="", flush=True)
    result["financial_indicator"] = fetch_financial_indicator(code)
    result["profit_statement"] = fetch_profit_statement(code)
    result["balance_sheet"] = fetch_balance_sheet(code)
    result["cashflow"] = fetch_cashflow(code)
    result["annual_financial"] = fetch_annual_financial(code)
    print("✓")

    # 5. 股东治理
    print(f"  [5/10] 采集股东信息...", end="", flush=True)
    result["top10_holders"] = fetch_top10_holders(code)
    result["pledge_ratio"] = fetch_pledge_ratio(code)
    result["holder_num"] = fetch_holder_num(code)
    result["management_changes"] = fetch_management_changes(code)
    print("✓")

    # 6. 资金流向
    print(f"  [6/10] 采集资金流向...", end="", flush=True)
    result["fund_flow"] = fetch_sector_fund_flow(code)
    print("✓" if result["fund_flow"] else "⚠ 失败")

    # 7. 估值历史
    print(f"  [7/10] 采集估值历史...", end="", flush=True)
    result["valuation_history"] = fetch_valuation_history(code)
    print("✓" if result["valuation_history"] else "⚠ 失败")

    # 8. 机构研报与龙虎榜
    print(f"  [8/10] 采集研报与龙虎榜...", end="", flush=True)
    result["research_reports"] = fetch_research_reports(code)
    result["analyst_consensus"] = fetch_analyst_consensus(code)
    result["dragon_tiger"] = fetch_dragon_tiger(code)
    print("✓")

    # 9. 市场情绪与指数
    print(f"  [9/10] 采集市场情绪...", end="", flush=True)
    result["market_sentiment"] = fetch_market_sentiment()
    result["index_data"] = fetch_index_data()
    print("✓")

    # 10. 行业信息
    print(f"  [10/10] 采集行业信息...", end="", flush=True)
    industry = (result.get("stock_info") or {}).get("industry", "")
    if industry:
        result["industry_peers"] = fetch_industry_rank(industry)[:10]
    else:
        result["industry_peers"] = []
    print("✓")

    return result
