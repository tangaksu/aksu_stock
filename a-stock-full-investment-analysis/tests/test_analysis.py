from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analyzers.base import ModuleResult, calc_trade_levels, position_from_total_score
from analyzers.m06_technical import analyze_technical
from analyzers.m16_summary import calc_weighted_score
from main import run_multi
from report_generator import generate_report


class FakeSeries:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return list(self._values)


class FakeFrame:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.columns = list(rows[0].keys()) if rows else []
        self.empty = not rows

    def __getitem__(self, key):
        return FakeSeries([row[key] for row in self._rows])


def make_kline(days: int = 140) -> FakeFrame:
    rows = []
    for idx in range(days):
        close = 10 + idx * 0.18 + (idx % 5) * 0.03
        rows.append({
            "日期": f"2026-01-{(idx % 28) + 1:02d}",
            "开盘": round(close - 0.12, 2),
            "收盘": round(close, 2),
            "最高": round(close + 0.2, 2),
            "最低": round(close - 0.2, 2),
            "成交量": 100000 + idx * 1200,
            "成交额": (100000 + idx * 1200) * close,
        })
    return FakeFrame(rows)


class AnalysisTests(unittest.TestCase):
    def test_calc_trade_levels_and_position(self):
        levels = calc_trade_levels(100.0, 96.0, 93.0)
        self.assertEqual(levels["entry_low"], 96.0)
        self.assertEqual(levels["entry_high"], 102.0)
        self.assertEqual(levels["stop_loss"], 93.0)
        self.assertEqual(position_from_total_score(85), "20-35%")
        self.assertEqual(position_from_total_score(55), "0%")

    def test_m06_outputs_multicycle_metrics(self):
        data = {
            "realtime": {"price": 35.2, "pct_change": 2.8},
            "kline_df": make_kline(),
            "_meta": {"kline_df": {"source": "测试K线", "message": "采集成功"}},
        }
        result = analyze_technical(data)
        joined = "\n".join(result.key_findings)
        self.assertIn("多周期趋势", joined)
        self.assertIn("KDJ", joined)
        self.assertIn("支撑/压力", joined)
        self.assertIn("技术形态", joined)
        self.assertIn("weekly_trend", result.detail)

    def test_report_contains_meta_and_no_silent_na(self):
        data = {
            "code": "600519",
            "fetch_time": "2026-06-29T12:00:00",
            "realtime": {"name": "测试股份", "price": 123.45, "pct_change": 1.23},
            "stock_info": {"industry": "消费", "board": "主板"},
            "_meta": {
                "realtime": {
                    "source": "东方财富/AKShare",
                    "fetched_at": "2026-06-29T12:00:00",
                    "success": True,
                    "message": "采集成功",
                },
                "kline_df": {
                    "source": "腾讯财经",
                    "fetched_at": "2026-06-29T12:00:01",
                    "success": False,
                    "message": "⚠️ 数据获取失败（上游接口未返回有效内容）",
                },
            },
            "data_quality": {"failed_sections": ["kline_df"]},
        }
        module_results = {
            "M01": ModuleResult("M01", "模块1", 8.0, 4, ["✅ 基本面亮点"], conclusion="ok"),
            "M02": ModuleResult("M02", "模块2", 7.0, 4, ["✅ 财务稳健"], conclusion="ok"),
            "M03": ModuleResult("M03", "模块3", 7.0, 4, ["⚠️ 股东变动"], conclusion="ok"),
            "M04": ModuleResult("M04", "模块4", 7.0, 4, ["✅ 行业景气"], conclusion="ok"),
            "M05": ModuleResult("M05", "模块5", 7.0, 4, ["✅ 估值合理"], conclusion="ok"),
            "M06": ModuleResult("M06", "模块6", 7.0, 4, ["✅ 技术修复"], conclusion="ok", detail={"stance": "强势多头"}),
            "M07": ModuleResult("M07", "模块7", 7.0, 4, ["✅ 资金回流"], conclusion="ok"),
            "M08": ModuleResult("M08", "模块8", 7.0, 4, ["✅ 题材活跃"], conclusion="ok"),
            "M09": ModuleResult("M09", "模块9", 7.0, 4, ["✅ 机构看多"], conclusion="ok"),
            "M10": ModuleResult("M10", "模块10", 7.0, 4, ["✅ 大盘配合"], conclusion="ok"),
            "M11": ModuleResult("M11", "模块11", 7.0, 4, ["✅ 流动性充裕"], conclusion="ok"),
            "M12": ModuleResult("M12", "模块12", 7.0, 4, ["✅ 催化明确"], conclusion="ok"),
            "M13": ModuleResult("M13", "模块13", 7.0, 4, ["✅ 历史低位"], conclusion="ok"),
            "M14": ModuleResult("M14", "模块14", 7.0, 4, ["⚠️ 需控仓"], conclusion="ok"),
        }
        total_score = calc_weighted_score(module_results)
        module_results["M16"] = ModuleResult(
            "M16",
            "总结",
            round(total_score / 10, 1),
            4,
            ["✅ 综合亮点"],
            conclusion="ok",
            detail={
                "total_score": total_score,
                "stars": 4,
                "rating_name": "优质标的",
                "risk_level": "中低风险",
                "color": "#16a34a",
                "position": "20-35% 分层配置",
                "ma10": 120.1,
                "ma20": 118.3,
                "highlights": ["基本面亮点"],
                "risks": ["需控仓"],
            },
        )
        html = generate_report(data, module_results)
        self.assertIn("数据采集追踪表", html)
        self.assertIn("报告降级说明", html)
        self.assertNotIn("N/A", html)
        self.assertIn("v4.0.0", html)

    def test_run_multi_still_outputs_comparison_table(self):
        fake_hist = make_kline(60)
        fake_realtime = {
            "600519": {"name": "茅台", "price": 1500.0, "pct_change": 1.2, "turnover_rate": 1.1},
            "000858": {"name": "五粮液", "price": 130.0, "pct_change": -0.5, "turnover_rate": 2.3},
        }
        with patch("data_collector.fetch_realtime", return_value=fake_realtime), patch("data_collector.fetch_hist_kline", return_value=fake_hist):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                run_multi(["600519", "000858"])
        output = buffer.getvalue()
        self.assertIn("多股对比分析", output)
        self.assertIn("代码", output)
        self.assertIn("600519", output)


if __name__ == "__main__":
    unittest.main()
