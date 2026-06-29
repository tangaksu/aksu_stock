"""
test_analyzers.py — 分析模块单元测试
验证：
  1. 每个模块用最小合法 data 字典能正常运行
  2. 用空数据字典（全降级）能正常运行
  3. ModuleResult 字段满足约束（score in [1,10]，stars in [1,5]，结论非空）
"""
import sys
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analyzers import (
    analyze_business,
    analyze_financial,
    analyze_governance,
    analyze_industry,
    analyze_valuation,
    analyze_technical,
    analyze_capital,
    analyze_sentiment,
    analyze_consensus,
    analyze_market,
    analyze_liquidity,
    analyze_catalyst,
    analyze_history,
    analyze_risk_control,
    analyze_peer,
    analyze_timing,
    analyze_summary,
    ModuleResult,
)


# ─────────────────────────────────────────────────────────
# 测试数据工厂
# ─────────────────────────────────────────────────────────

def _minimal_data() -> dict:
    """包含核心字段的最小数据字典"""
    import pandas as pd
    import numpy as np

    n = 130
    rng = np.random.default_rng(0)
    prices = 100 + np.cumsum(rng.normal(0, 1, n))

    kline = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=n),
        "open": prices * 0.999,
        "high": prices * 1.005,
        "low": prices * 0.994,
        "close": prices,
        "volume": np.abs(rng.normal(1e6, 1e5, n)),
        "amount": np.abs(rng.normal(1e8, 1e7, n)),
        "turnover_rate": rng.uniform(1, 5, n),
    })

    fin = pd.DataFrame({
        "报告期": ["2023-09-30", "2023-06-30", "2023-03-31", "2022-12-31"],
        "营业收入": [1e10, 9e9, 8e9, 3e10],
        "净利润": [3e9, 2.7e9, 2.4e9, 9e9],
        "扣非净利润": [2.9e9, 2.6e9, 2.3e9, 8.8e9],
        "毛利率": [45.0, 44.0, 43.0, 42.0],
        "净利率": [30.0, 29.5, 29.0, 28.0],
        "ROE": [25.0, 24.0, 23.0, 22.0],
        "经营现金流": [3.2e9, 2.9e9, 2.6e9, 9.5e9],
        "分红率": [50.0, 0, 0, 52.0],
    })

    balance = pd.DataFrame({
        "报告期": ["2023-09-30"],
        "总资产": [5e10],
        "总负债": [2e10],
        "货币资金": [1.5e10],
        "有息负债": [5e9],
        "商誉": [1e8],
        "存货": [2e9],
        "应收账款": [8e8],
    })

    return {
        "code": "600519",
        "name": "贵州茅台",
        "price": 1888.0,
        "prev_close": 1870.0,
        "open": 1865.0,
        "high": 1900.0,
        "low": 1860.0,
        "volume": 50000,
        "amount": 1e9,
        "turnover_rate": 0.3,
        "pct_change": 0.95,
        "pe_ttm": 38.5,
        "pb": 12.0,
        "market_cap": 2.37e12,
        "circulate_cap": 2.1e12,
        "week52_high": 2000.0,
        "week52_low": 1600.0,
        "week52_position": 72.0,
        "industry": "白酒",
        "concept": ["白酒", "贵州国资", "消费龙头"],
        "list_date": "2001-08-27",
        "total_shares": 1.26e9,
        "float_shares": 1.26e9,
        "kline": kline,
        "technical": {
            "ma5": prices[-1] * 0.998,
            "ma10": prices[-1] * 0.995,
            "ma20": prices[-1] * 0.990,
            "ma60": prices[-1] * 0.980,
            "ma120": prices[-1] * 0.970,
            "rsi": 55.0,
            "macd": 2.5,
            "macd_signal": 2.0,
            "macd_hist": 0.5,
            "kdj_k": 60.0,
            "kdj_d": 55.0,
            "kdj_j": 70.0,
            "boll_upper": prices[-1] * 1.03,
            "boll_mid": prices[-1],
            "boll_lower": prices[-1] * 0.97,
        },
        "financial": fin,
        "balance_sheet": balance,
        "cashflow": pd.DataFrame({
            "报告期": ["2023-09-30"],
            "经营活动现金流净额": [3.2e9],
        }),
        "top10_holders": [
            {"holder_name": "茅台集团", "hold_ratio": 54.0, "hold_change": "不变"},
            {"holder_name": "香港中央结算", "hold_ratio": 8.2, "hold_change": "增加"},
        ],
        "pledge_ratio": 0.0,
        "holder_num": 140000,
        "holder_num_change": -5000,
        "fund_flow": {
            "main_net": 2e7,
            "main_in": 8e7,
            "main_out": 6e7,
            "main_net_5d": 8e7,
            "main_net_10d": 1.5e8,
        },
        "north_fund": {"net_buy": 3e8, "cumulative_7d": 8e8},
        "research_reports": [
            {"title": "茅台Q3业绩超预期", "date": "2023-10-15", "rating": "买入", "target": 2100},
        ],
        "analyst_ratings": {
            "buy": 25, "add": 5, "neutral": 2, "reduce": 0,
            "target_high": 2300, "target_low": 1800, "target_avg": 2100,
        },
        "peers": [
            {"code": "000858", "name": "五粮液", "price": 160, "pe_ttm": 22, "market_cap_yi": 6200, "pct_change": 1.2},
            {"code": "000568", "name": "泸州老窖", "price": 190, "pe_ttm": 25, "market_cap_yi": 2900, "pct_change": 0.8},
        ],
        "dragon_tiger": [],
        "concepts": ["白酒", "消费龙头"],
        "market_sentiment": {
            "up_count": 2500,
            "down_count": 1000,
            "zt_count": 50,
            "dt_count": 5,
            "limit_up_ratio": 2.0,
        },
        "_meta": {},
    }


def _empty_data() -> dict:
    """全空数据（降级场景）"""
    return {"code": "000001", "name": "平安银行", "_meta": {}}


# ─────────────────────────────────────────────────────────
# 通用约束验证
# ─────────────────────────────────────────────────────────

def _assert_module_result(tc: unittest.TestCase, r: ModuleResult, mid: str):
    tc.assertIsInstance(r, ModuleResult, f"{mid}: 应返回 ModuleResult")
    tc.assertGreaterEqual(r.score, 1.0, f"{mid}: score >= 1")
    tc.assertLessEqual(r.score, 10.0, f"{mid}: score <= 10")
    tc.assertIn(r.stars, range(1, 6), f"{mid}: stars in [1,5]")
    tc.assertIsInstance(r.key_findings, list, f"{mid}: key_findings 应为 list")
    tc.assertTrue(r.conclusion, f"{mid}: conclusion 不能为空")


# ─────────────────────────────────────────────────────────
# M01-M15 参数化测试
# ─────────────────────────────────────────────────────────

_SIMPLE_MODULES = [
    ("M01", analyze_business),
    ("M02", analyze_financial),
    ("M03", analyze_governance),
    ("M04", analyze_industry),
    ("M05", analyze_valuation),
    ("M06", analyze_technical),
    ("M07", analyze_capital),
    ("M08", analyze_sentiment),
    ("M09", analyze_consensus),
    ("M10", analyze_market),
    ("M11", analyze_liquidity),
    ("M12", analyze_catalyst),
    ("M13", analyze_history),
    ("M14", analyze_risk_control),
    ("M15", analyze_peer),
]


class TestModulesWithMinimalData(unittest.TestCase):
    def _run(self, mid, func):
        r = func(_minimal_data())
        _assert_module_result(self, r, mid)


class TestModulesWithEmptyData(unittest.TestCase):
    def _run(self, mid, func):
        r = func(_empty_data())
        _assert_module_result(self, r, mid)


# 动态生成测试方法
for _mid, _func in _SIMPLE_MODULES:
    def _make_minimal_test(mid, func):
        def test(self):
            self._run(mid, func)
        test.__name__ = f"test_{mid.lower()}_minimal"
        return test

    def _make_empty_test(mid, func):
        def test(self):
            self._run(mid, func)
        test.__name__ = f"test_{mid.lower()}_empty"
        return test

    setattr(TestModulesWithMinimalData, f"test_{_mid.lower()}_minimal", _make_minimal_test(_mid, _func))
    setattr(TestModulesWithEmptyData, f"test_{_mid.lower()}_empty", _make_empty_test(_mid, _func))


# ─────────────────────────────────────────────────────────
# M16 择时模块特殊测试
# ─────────────────────────────────────────────────────────

class TestM16Timing(unittest.TestCase):
    def test_minimal(self):
        r = analyze_timing(_minimal_data())
        _assert_module_result(self, r, "M16")
        ts = r.detail.get("timing_score")
        self.assertIsNotNone(ts)
        self.assertGreaterEqual(ts, 0)
        self.assertLessEqual(ts, 100)

    def test_empty(self):
        r = analyze_timing(_empty_data())
        _assert_module_result(self, r, "M16")

    def test_detail_keys(self):
        r = analyze_timing(_minimal_data())
        for key in ("timing_score", "timing_level", "operation", "dim1_technical", "dim2_valuation"):
            self.assertIn(key, r.detail, f"M16 detail 缺少字段 {key}")


# ─────────────────────────────────────────────────────────
# M17 综合汇总测试
# ─────────────────────────────────────────────────────────

class TestM17Summary(unittest.TestCase):
    def _make_module_results(self, data):
        results = {}
        for mid, func in _SIMPLE_MODULES:
            results[mid] = func(data)
        results["M16"] = analyze_timing(data)
        return results

    def test_minimal(self):
        data = _minimal_data()
        mods = self._make_module_results(data)
        r = analyze_summary(data, mods)
        _assert_module_result(self, r, "M17")

    def test_total_score_range(self):
        data = _minimal_data()
        mods = self._make_module_results(data)
        r = analyze_summary(data, mods)
        ts = r.detail.get("total_score")
        self.assertIsNotNone(ts)
        self.assertGreaterEqual(ts, 0)
        self.assertLessEqual(ts, 100)

    def test_stars_match_score(self):
        data = _minimal_data()
        mods = self._make_module_results(data)
        r = analyze_summary(data, mods)
        ts = r.detail.get("total_score", 0)
        stars = r.detail.get("stars")
        if ts >= 90:
            self.assertEqual(stars, 5)
        elif ts >= 80:
            self.assertEqual(stars, 4)
        elif ts >= 70:
            self.assertEqual(stars, 3)
        elif ts >= 60:
            self.assertEqual(stars, 2)
        else:
            self.assertEqual(stars, 1)

    def test_empty(self):
        data = _empty_data()
        mods = self._make_module_results(data)
        r = analyze_summary(data, mods)
        _assert_module_result(self, r, "M17")

    def test_dim_scores_present(self):
        data = _minimal_data()
        mods = self._make_module_results(data)
        r = analyze_summary(data, mods)
        dim_scores = r.detail.get("dim_scores", {})
        for dim in ("基本面", "行业估值", "市场博弈", "风控催化"):
            self.assertIn(dim, dim_scores)


if __name__ == "__main__":
    unittest.main(verbosity=2)
