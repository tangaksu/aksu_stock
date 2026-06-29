#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股机构级全维度股票投资分析报告生成技能
入口：python3 main.py --code 600519

用法:
  python3 main.py --code 600519
  python3 main.py --code 000858 --output report.html
  python3 main.py --code 600519,000858,002304 --mode multi
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

# 确保能找到本目录下的模块
sys.path.insert(0, os.path.dirname(__file__))


def run_single(code: str, output: str | None = None) -> str:
    """执行单股全维度分析，返回 HTML 报告路径"""
    from data_collector import collect_all_data
    from analyzers.m01_business import analyze_business
    from analyzers.m02_financial import analyze_financial
    from analyzers.m03_governance import analyze_governance
    from analyzers.m04_industry import analyze_industry
    from analyzers.m05_valuation import analyze_valuation
    from analyzers.m06_technical import analyze_technical
    from analyzers.m07_capital import analyze_capital
    from analyzers.m08_sentiment import analyze_sentiment
    from analyzers.m09_consensus import analyze_consensus
    from analyzers.m10_market import analyze_market
    from analyzers.m11_liquidity import analyze_liquidity
    from analyzers.m12_catalyst import analyze_catalyst
    from analyzers.m13_history import analyze_history
    from analyzers.m14_risk_control import analyze_risk_control
    from analyzers.m15_peer import analyze_peer
    from analyzers.m16_summary import analyze_summary
    from report_generator import generate_report

    print(f"\n{'='*60}")
    print(f"  A股机构级全维度分析报告 — {code}")
    print(f"{'='*60}")
    print(f"\n[Step 1/3] 数据采集中...")

    data = collect_all_data(code)

    print(f"\n[Step 2/3] 16大模块分析中...")
    module_results = {}

    analyzers = [
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

    for mid, fn in analyzers:
        try:
            if mid == "M14":
                module_results[mid] = fn(data, module_results)
            else:
                module_results[mid] = fn(data)
            score = module_results[mid].score
            print(f"  {mid} ✓ ({score:.1f}/10)")
        except Exception as e:
            print(f"  {mid} ⚠ 分析异常: {e}")

    # M16 综合总结
    try:
        module_results["M16"] = analyze_summary(data, module_results)
        total = module_results["M16"].detail.get("total_score", 0)
        stars = module_results["M16"].detail.get("stars", 0)
        rating = module_results["M16"].detail.get("rating_name", "")
        print(f"  M16 ✓ 综合评分: {total:.1f}/100 {'★'*stars} {rating}")
    except Exception as e:
        print(f"  M16 ⚠ 综合评分异常: {e}")

    print(f"\n[Step 3/3] 生成 HTML 报告...")

    html = generate_report(data, module_results)

    # 确定输出路径
    if not output:
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        output = f"report_{code}_{date_str}.html"

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{'='*60}")
    print(f"  ✅ 报告生成完成！")
    print(f"  📄 文件路径：{os.path.abspath(output)}")

    if "M16" in module_results:
        d = module_results["M16"].detail
        print(f"  🏆 综合评分：{d.get('total_score', 0):.1f}/100")
        print(f"  ⭐ 星级评级：{'★' * d.get('stars', 0)} {d.get('rating_name', '')}")
        print(f"  ⚠️ 风险等级：{d.get('risk_level', '')}")
        print(f"  📦 建议仓位：{d.get('position', '')}")
    print(f"{'='*60}\n")

    return output


def run_multi(codes: list[str]) -> None:
    """多股对比分析（简版，输出对比表格）"""
    from data_collector import fetch_realtime, fetch_hist_kline

    print(f"\n多股对比分析：{', '.join(codes)}")
    print("-" * 80)

    rt_map = fetch_realtime(codes)

    rows = []
    for code in codes:
        rt = rt_map.get(code) or {}
        df = fetch_hist_kline(code, days_back=60)
        closes = []
        if df is not None and not df.empty:
            close_col = "收盘" if "收盘" in df.columns else "close"
            closes = df[close_col].tolist()

        ma20 = round(sum(closes[-20:]) / 20, 2) if len(closes) >= 20 else None
        price = rt.get("price")
        pct = rt.get("pct_change") or 0
        pos = round((price - min(closes[-60:])) / (max(closes[-60:]) - min(closes[-60:])) * 100, 1) if closes and price and max(closes[-60:]) > min(closes[-60:]) else None

        rows.append({
            "代码": code,
            "名称": rt.get("name", code),
            "价格": price,
            "涨跌幅": pct,
            "MA20": ma20,
            "MA20偏离": round((price - ma20) / ma20 * 100, 1) if price and ma20 else None,
            "60日位置%": pos,
            "换手率%": rt.get("turnover_rate"),
        })

    # 按60日位置排序
    rows.sort(key=lambda x: x.get("60日位置%") or 50)

    print(f"{'代码':>8}{'名称':>10}{'价格':>10}{'涨跌%':>8}{'MA20偏%':>10}{'60日位%':>10}{'换手%':>8}")
    print("-" * 70)
    for r in rows:
        print(
            f"{r['代码']:>8}{r['名称']:>10}"
            f"{r['价格'] or 0:>10.2f}"
            f"{r['涨跌幅'] or 0:>8.2f}"
            f"{r['MA20偏离'] or 0:>10.2f}"
            f"{r['60日位置%'] or 0:>10.1f}"
            f"{r['换手率%'] or 0:>8.2f}"
        )
    print("-" * 70)
    print("\n建议：60日位置<20%的标的具备底部布局价值，MA20偏离>10%需注意追高风险")


def main():
    parser = argparse.ArgumentParser(
        description="A股机构级全维度股票投资分析报告生成技能 v3.5.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python3 main.py --code 600519                    # 贵州茅台全维度分析
  python3 main.py --code 000858 --output r.html    # 指定输出文件
  python3 main.py --code 600519,000858,002304      # 多股对比
""",
    )
    parser.add_argument("--code", required=True, help="股票代码，多股用英文逗号分隔")
    parser.add_argument("--output", default=None, help="输出HTML文件路径（单股模式）")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "single", "multi"],
        help="分析模式：auto自动识别，single单股全维度，multi多股对比",
    )

    args = parser.parse_args()

    codes = [c.strip() for c in args.code.split(",") if c.strip()]

    if not codes:
        print("❌ 错误：请提供有效的股票代码")
        sys.exit(1)

    # 校验代码格式（6位数字为标准A股代码）
    for c in codes:
        if not (c.isdigit() and len(c) == 6):
            print(f"⚠️ 警告：'{c}' 不是标准6位数字A股代码（如600519/000858），可能导致数据获取失败")

    if args.mode == "multi" or (args.mode == "auto" and len(codes) > 1):
        run_multi(codes)
    else:
        run_single(codes[0], args.output)


if __name__ == "__main__":
    main()
