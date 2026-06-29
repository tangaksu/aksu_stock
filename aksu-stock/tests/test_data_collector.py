"""
test_data_collector.py — 数据采集层单元测试（全部 mock，无真实网络请求）
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 确保 aksu-stock 目录在 sys.path 中
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import data_collector as dc


class TestSafeHelpers(unittest.TestCase):
    def test_safe_float_valid(self):
        self.assertAlmostEqual(dc._safe_float("3.14"), 3.14)

    def test_safe_float_invalid(self):
        self.assertIsNone(dc._safe_float("N/A"))
        self.assertIsNone(dc._safe_float(None))
        self.assertIsNone(dc._safe_float(""))

    def test_tencent_prefix_sh(self):
        self.assertEqual(dc._tencent_prefix("600519"), "sh600519")
        self.assertEqual(dc._tencent_prefix("688001"), "sh688001")
        self.assertEqual(dc._tencent_prefix("900901"), "sh900901")

    def test_tencent_prefix_sz(self):
        self.assertEqual(dc._tencent_prefix("000001"), "sz000001")
        self.assertEqual(dc._tencent_prefix("300750"), "sz300750")


class TestWithMeta(unittest.TestCase):
    def test_with_meta_dict_success(self):
        # _with_meta(dict, source, success=True, message="")
        result = dc._with_meta({"price": 100.0}, "AKShare")
        self.assertEqual(result["price"], 100.0)
        self.assertTrue(result.get("_success"))
        self.assertEqual(result["_source"], "AKShare")

    def test_with_meta_scalar_wraps(self):
        result = dc._with_meta(99.5, "Tencent")
        self.assertEqual(result["data"], 99.5)
        self.assertTrue(result.get("_success"))

    def test_with_meta_failure(self):
        result = dc._with_meta({}, "AKShare", success=False, message="⚠️ 失败")
        self.assertFalse(result["_success"])
        self.assertIn("⚠️", result["_message"])

    def test_failure_helper(self):
        result = dc._failure("AKShare", "⚠️ 数据获取失败")
        self.assertFalse(result["_success"])

    def test_set_field_success(self):
        result = {"_meta": {}}
        payload = dc._with_meta({"data": 99.5}, "Tencent")
        dc._set_field(result, "price", payload)
        self.assertEqual(result["price"], 99.5)
        self.assertTrue(result["_meta"]["price"]["success"])

    def test_set_field_failure(self):
        result = {"_meta": {}}
        payload = dc._failure("AKShare", "⚠️ 数据获取失败")
        dc._set_field(result, "price", payload)
        self.assertFalse(result["_meta"]["price"]["success"])


# data_collector uses _http_get (urllib.request) — patch at module level
TENCENT_MOCK = 'v_sh600519="1~贵州茅台~600519~1888.88~1870.00~1865.00~50000~25000~25000~1900.00~1888.00~1~5~60000000~1000000000~0.95~50.00~25000~1~1~0~0~0~0~0~0~0~0~0~0~0~0~0.32~1800~2000~15~1~2023-06-29~50000000000~30000000000~10.00";'
SINA_MOCK = 'var hq_str_sh600519="贵州茅台,1865.00,1870.00,1888.88,1900.00,1800.00,1888.50,1889.00,50000,94444000.00,100,1888.50,200,1888.00,300,1887.00,400,1886.00,500,1885.00,100,1889.00,200,1890.00,300,1891.00,400,1892.00,500,1893.00,2023-06-29,15:00:00,00,";'


class TestTencentRealtime(unittest.TestCase):
    @patch("data_collector._http_get")
    def test_tencent_returns_price(self, mock_http):
        mock_http.return_value = TENCENT_MOCK
        result = dc.fetch_realtime_tencent("600519")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("_success"))
        self.assertAlmostEqual(result["price"], 1888.88, places=1)
        self.assertEqual(result["name"], "贵州茅台")

    @patch("data_collector._http_get", return_value=None)
    def test_tencent_returns_none_on_error(self, mock_http):
        result = dc.fetch_realtime_tencent("600519")
        self.assertIsNone(result)


class TestSinaRealtime(unittest.TestCase):
    @patch("data_collector._http_get")
    def test_sina_returns_price(self, mock_http):
        mock_http.return_value = SINA_MOCK
        result = dc.fetch_realtime_sina("600519")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("_success"))
        self.assertAlmostEqual(result["price"], 1888.88, places=1)

    @patch("data_collector._http_get", return_value=None)
    def test_sina_returns_none_on_missing(self, mock_http):
        result = dc.fetch_realtime_sina("600519")
        self.assertIsNone(result)


class TestCalcTechnicalIndicators(unittest.TestCase):
    """使用合成 K 线数据验证技术指标计算"""
    def _make_kline(self, n: int):
        import pandas as pd
        import numpy as np
        rng = np.random.default_rng(42)
        prices = 100 + np.cumsum(rng.normal(0, 1, n))
        df = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=n),
            "open": prices * 0.999,
            "high": prices * 1.005,
            "low": prices * 0.994,
            "close": prices,
            "volume": np.abs(rng.normal(1e6, 1e5, n)),
            "amount": np.abs(rng.normal(1e8, 1e7, n)),
        })
        return df

    def test_indicators_keys(self):
        df = self._make_kline(130)
        ind = dc.calc_technical_indicators(df)
        # actual key names from data_collector: rsi14, macd (top-level via update), boll (nested)
        for key in ("ma5", "ma10", "ma20", "ma60", "rsi14", "macd", "boll"):
            self.assertIn(key, ind, f"Expected key '{key}' in indicators")

    def test_indicators_short_kline(self):
        df = self._make_kline(10)
        ind = dc.calc_technical_indicators(df)
        # ma60 needs 60 rows → should be None
        self.assertIsNone(ind.get("ma60"))
        # ma5 needs 5 rows → should be present
        self.assertIsNotNone(ind.get("ma5"))

    def test_indicators_empty(self):
        import pandas as pd
        ind = dc.calc_technical_indicators(pd.DataFrame())
        self.assertIsInstance(ind, dict)
        self.assertEqual(len(ind), 0)


class TestCollectAllDataDegraded(unittest.TestCase):
    """全降级模式：AKShare 不可用 + HTTP 返回 None，collect_all_data 应正常返回空数据字典"""
    def test_degraded_returns_dict(self):
        with patch.object(dc, "_get_ak", return_value=None), \
             patch("data_collector._http_get", return_value=None):
            result = dc.collect_all_data("600519")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("code"), "600519")
        self.assertIn("_meta", result)

    def test_degraded_meta_all_failed(self):
        with patch.object(dc, "_get_ak", return_value=None), \
             patch("data_collector._http_get", return_value=None):
            result = dc.collect_all_data("600519")
        meta = result.get("_meta", {})
        # 至少有一个字段的 meta 记录
        self.assertGreater(len(meta), 0)
        # 所有已记录字段均为 failed
        for field, info in meta.items():
            self.assertFalse(info.get("success"), f"期望字段 {field} 失败，但 success=True")


class TestRuntimeDiagnostics(unittest.TestCase):
    def test_returns_dict_with_akshare_key(self):
        # runtime_diagnostics returns {"akshare": {...}, host: {...}, ...}
        diag = dc.runtime_diagnostics()
        self.assertIn("akshare", diag)
        self.assertIn("available", diag["akshare"])


if __name__ == "__main__":
    unittest.main()
