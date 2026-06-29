#!/usr/bin/env python3
"""
main.py — aksu-stock v5.1.5 CLI 入口

用法:
    python3 main.py --code 600519
    python3 main.py --code 600519 --output ./reports/
    python3 main.py --code 600519,000858,000001  # 多股对比模式
    python3 main.py --code 600519 --diagnose      # 仅诊断数据源
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time

# ── 路径修正（在 aksu-stock/ 目录执行时保证 import 正常）
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from data_collector import collect_all_data, runtime_diagnostics
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
)
from report_generator import generate_report


# ── 校验股票代码 ──────────────────────────────────────────

def _validate_code(code: str) -> str:
    code = code.strip()
    if not code.isdigit() or len(code) != 6:
        raise ValueError(f"股票代码格式错误：'{code}'，应为6位数字（如 600519）")
    return code


# ── 运行全部分析模块 ──────────────────────────────────────

_ANALYZERS = {
    "M01": analyze_business,
    "M02": analyze_financial,
    "M03": analyze_governance,
    "M04": analyze_industry,
    "M05": analyze_valuation,
    "M06": analyze_technical,
    "M07": analyze_capital,
    "M08": analyze_sentiment,
    "M09": analyze_consensus,
    "M10": analyze_market,
    "M11": analyze_liquidity,
    "M12": analyze_catalyst,
    "M13": analyze_history,
    "M14": analyze_risk_control,
    "M15": analyze_peer,
    "M16": analyze_timing,
}


def run_analysis(code: str, verbose: bool = False) -> tuple[dict, dict]:
    """采集数据 + 运行 17 个分析模块，返回 (data, module_results)"""
    if verbose:
        print(f"  [1/3] 采集数据 {code} …", flush=True)
    data = collect_all_data(code)

    if verbose:
        print(f"  [2/3] 运行分析模块 M01-M16 …", flush=True)
    module_results = {}
    for mid, func in _ANALYZERS.items():
        try:
            module_results[mid] = func(data)
        except Exception as exc:
            from analyzers.base import ModuleResult
            module_results[mid] = ModuleResult(
                module_id=mid,
                module_name=mid,
                score=5.0,
                stars=3,
                key_findings=[f"⚠️ 模块执行异常: {exc}"],
                short_advice="暂无",
                mid_advice="暂无",
                long_advice="暂无",
                conclusion=f"模块 {mid} 运行时异常",
            )

    if verbose:
        print(f"  [3/3] 综合汇总 M17 …", flush=True)
    try:
        module_results["M17"] = analyze_summary(data, module_results)
    except Exception as exc:
        from analyzers.base import ModuleResult
        module_results["M17"] = ModuleResult(
            module_id="M17",
            module_name="综合汇总",
            score=5.0,
            stars=3,
            key_findings=[f"⚠️ 综合汇总异常: {exc}"],
            short_advice="暂无",
            mid_advice="暂无",
            long_advice="暂无",
            conclusion="M17 运行时异常",
        )

    return data, module_results


# ── 单股报告 ─────────────────────────────────────────────

def generate_single(code: str, output_dir: str, verbose: bool = False) -> str:
    code = _validate_code(code)
    t0 = time.time()

    if verbose:
        print(f"\n{'═'*50}")
        print(f" aksu-stock v5.1.5 — 分析 {code}")
        print(f"{'═'*50}")

    data, module_results = run_analysis(code, verbose=verbose)
    name = data.get("name") or code

    html = generate_report(data, module_results)

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{code}_{name}_分析报告.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    elapsed = time.time() - t0
    m17 = module_results.get("M17")
    m16 = module_results.get("M16")
    ts = m17.detail.get("total_score", 0) if m17 else 0
    tl = m16.detail.get("timing_score", 0) if m16 else 0
    stars = m17.detail.get("stars", 0) if m17 else 0
    rating = m17.detail.get("rating_name", "—") if m17 else "—"

    if verbose:
        print(f"\n✅ 分析完成（{elapsed:.1f}s）")
        print(f"   综合投资价值：{ts:.1f}/100 {'★'*stars}{'☆'*(5-stars)} {rating}")
        print(f"   现价交易择时：{tl:.1f}/100")
        print(f"   报告已保存：{filename}")

    return filename


# ── 多股对比 ─────────────────────────────────────────────

def generate_multi(codes: list[str], output_dir: str, verbose: bool = False) -> str:
    results = []
    for code in codes:
        code = _validate_code(code)
        if verbose:
            print(f"\n▶ 分析 {code} …")
        data, module_results = run_analysis(code, verbose=verbose)
        m17 = module_results.get("M17")
        m16 = module_results.get("M16")
        results.append({
            "code": code,
            "name": data.get("name") or code,
            "price": data.get("price"),
            "pct_change": data.get("pct_change"),
            "total_score": m17.detail.get("total_score", 0) if m17 else 0,
            "timing_score": m16.detail.get("timing_score", 0) if m16 else 0,
            "stars": m17.detail.get("stars", 1) if m17 else 1,
            "rating": m17.detail.get("rating_name", "—") if m17 else "—",
            "position": m17.detail.get("position", "—") if m17 else "—",
        })

    results.sort(key=lambda x: x["total_score"], reverse=True)

    rows_html = ""
    for r in results:
        pc = r.get("pct_change") or 0
        pct_c = "#dc3545" if pc < 0 else "#28a745"
        rows_html += f"""<tr>
          <td>{r['code']}</td>
          <td>{r['name']}</td>
          <td>{r['price'] or '—'}</td>
          <td style="color:{pct_c}">{pc:+.2f}%</td>
          <td style="font-weight:700;color:{'#28a745' if r['total_score']>=70 else '#dc3545'}">{r['total_score']:.1f}</td>
          <td style="font-weight:700">{r['timing_score']:.1f}</td>
          <td>{'★'*r['stars']}{'☆'*(5-r['stars'])}</td>
          <td>{r['rating']}</td>
          <td>{r['position']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>多股对比分析报告</title>
<style>
body{{font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;background:#f5f7fa;padding:20px;color:#333}}
h1{{font-size:22px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
th,td{{padding:10px 14px;text-align:right;border-bottom:1px solid #f0f0f0}}
th{{background:#f8f9fa;font-weight:700;text-align:center;color:#555}}
td:first-child,th:first-child{{text-align:left}}
tr:hover td{{background:#fafafa}}
</style>
</head>
<body>
<h1>📊 多股对比分析报告</h1>
<p style="color:#888;font-size:13px;margin-bottom:16px">共 {len(results)} 只，已按综合投资价值得分降序排列</p>
<table>
  <thead>
    <tr>
      <th>代码</th><th>名称</th><th>现价</th><th>涨跌%</th>
      <th>综合评分/100</th><th>择时评分/100</th><th>星级</th><th>评级</th><th>建议仓位</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
<p style="color:#856404;background:#fff3cd;border-radius:8px;padding:12px;margin-top:20px;font-size:12px">
  【风险提示】本分析基于公开市场数据，仅为投资参考，不构成任何投资建议。股市有风险，投资需谨慎。
</p>
</body>
</html>"""

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, "多股对比分析报告.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    if verbose:
        print(f"\n✅ 多股对比报告已保存：{filename}")

    return filename


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="aksu-stock v5.1.5 — A股机构级投研分析")
    parser.add_argument("--code", required=True, help="6位股票代码，多股用逗号分隔（如 600519,000858）")
    parser.add_argument("--output", default="./reports", help="报告输出目录（默认 ./reports）")
    parser.add_argument("--diagnose", action="store_true", help="仅诊断数据源可用性")
    parser.add_argument("--quiet", action="store_true", help="静默模式，仅输出文件路径")
    args = parser.parse_args()

    verbose = not args.quiet

    if args.diagnose:
        diag = runtime_diagnostics()
        print(json.dumps(diag, ensure_ascii=False, indent=2))
        sys.exit(0)

    codes = [c.strip() for c in args.code.split(",") if c.strip()]

    if len(codes) == 1:
        path = generate_single(codes[0], args.output, verbose=verbose)
        if args.quiet:
            print(path)
    else:
        path = generate_multi(codes, args.output, verbose=verbose)
        if args.quiet:
            print(path)


if __name__ == "__main__":
    main()
