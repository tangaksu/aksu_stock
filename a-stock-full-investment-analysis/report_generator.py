"""
HTML 报告生成器 — 输出机构级全维度股票分析报告
首屏置顶100分制综合评分看板，16大模块卡片式布局
"""
from __future__ import annotations
from datetime import datetime


def _score_color(score: float, mode: str = "100") -> str:
    """评分色阶"""
    if mode == "100":
        if score >= 90:
            return "#15803d"
        if score >= 80:
            return "#16a34a"
        if score >= 70:
            return "#ca8a04"
        if score >= 60:
            return "#ea580c"
        return "#dc2626"
    else:  # 10分制
        if score >= 8:
            return "#16a34a"
        if score >= 6:
            return "#ca8a04"
        return "#dc2626"


def _score_bg(score: float, mode: str = "100") -> str:
    """评分背景色"""
    if mode == "100":
        if score >= 90:
            return "#dcfce7"
        if score >= 80:
            return "#d1fae5"
        if score >= 70:
            return "#fef9c3"
        if score >= 60:
            return "#ffedd5"
        return "#fee2e2"
    else:
        if score >= 8:
            return "#d1fae5"
        if score >= 6:
            return "#fef9c3"
        return "#fee2e2"


def _stars_html(stars: int) -> str:
    filled = "★" * stars
    empty = "☆" * (5 - stars)
    return f'<span style="color:#f59e0b;font-size:1.2em">{filled}</span><span style="color:#d1d5db">{empty}</span>'


def _findings_html(findings: list[str]) -> str:
    items = []
    for f in findings:
        if "✅" in f:
            color = "#15803d"
            bg = "#f0fdf4"
            border = "#86efac"
        elif "🚨" in f:
            color = "#dc2626"
            bg = "#fef2f2"
            border = "#fca5a5"
        elif "⚠️" in f:
            color = "#b45309"
            bg = "#fffbeb"
            border = "#fcd34d"
        elif "🔍" in f:
            color = "#1d4ed8"
            bg = "#eff6ff"
            border = "#93c5fd"
        elif "---" in f:
            items.append(f'<li style="list-style:none;border-top:1px dashed #e5e7eb;margin:4px 0;padding:4px 0;font-weight:600;color:#374151">{f.replace("---","").strip()}</li>')
            continue
        else:
            color = "#374151"
            bg = "#f9fafb"
            border = "#e5e7eb"
        items.append(
            f'<li style="background:{bg};border-left:3px solid {border};'
            f'color:{color};padding:6px 10px;margin:4px 0;border-radius:4px;'
            f'font-size:0.88em;line-height:1.5">{f}</li>'
        )
    return '<ul style="list-style:none;padding:0;margin:0">' + "".join(items) + "</ul>"


def _module_card(result) -> str:
    """单个分析模块卡片"""
    sc = result.score
    color = _score_color(sc, "10")
    bg = _score_bg(sc, "10")

    advice_rows = ""
    if result.short_advice:
        advice_rows += f'<tr><td style="width:60px;font-weight:600;color:#6b7280;font-size:0.8em;white-space:nowrap;vertical-align:top;padding:3px 8px 3px 0">短线</td><td style="font-size:0.85em;color:#374151;padding:3px 0">{result.short_advice}</td></tr>'
    if result.mid_advice:
        advice_rows += f'<tr><td style="font-weight:600;color:#6b7280;font-size:0.8em;white-space:nowrap;vertical-align:top;padding:3px 8px 3px 0">中线</td><td style="font-size:0.85em;color:#374151;padding:3px 0">{result.mid_advice}</td></tr>'
    if result.long_advice:
        advice_rows += f'<tr><td style="font-weight:600;color:#6b7280;font-size:0.8em;white-space:nowrap;vertical-align:top;padding:3px 8px 3px 0">长线</td><td style="font-size:0.85em;color:#374151;padding:3px 0">{result.long_advice}</td></tr>'

    return f"""
<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;
            margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08)">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
    <div>
      <span style="background:#1e3a5f;color:#fff;font-size:0.75em;padding:2px 8px;
                   border-radius:4px;font-weight:600;margin-right:8px">{result.module_id}</span>
      <span style="font-size:1.05em;font-weight:700;color:#111827">{result.module_name}</span>
    </div>
    <div style="text-align:right">
      <div style="background:{bg};color:{color};font-size:1.4em;font-weight:800;
                  padding:4px 12px;border-radius:8px;display:inline-block">{sc:.1f}<span style="font-size:0.6em">/10</span></div>
      <div style="margin-top:2px">{_stars_html(result.stars)}</div>
    </div>
  </div>
  <div style="margin-bottom:12px">{_findings_html(result.key_findings[:12])}</div>
  {"" if not advice_rows else f'<div style="background:#f8fafc;border-radius:8px;padding:10px 12px;margin-top:10px"><table style="width:100%;border-collapse:collapse">{advice_rows}</table></div>'}
  <div style="margin-top:10px;padding:8px 12px;background:{bg};border-radius:6px;
              font-size:0.88em;font-weight:600;color:{color};border-left:3px solid {color}">
    💡 {result.conclusion}
  </div>
</div>
"""


def generate_report(data: dict, module_results: dict) -> str:
    """生成完整 HTML 投资分析报告"""
    rt = data.get("realtime") or {}
    info = data.get("stock_info") or {}
    code = data.get("code", "")
    name = rt.get("name") or info.get("name", code)
    price = rt.get("price", 0)
    pct = rt.get("pct_change") or 0
    industry = info.get("industry", "")
    board = info.get("board", "")
    fetch_time = data.get("fetch_time", datetime.now().isoformat())[:19]

    # 获取综合分析结果
    m16 = module_results.get("M16")
    summary_detail = m16.detail if m16 else {}
    total_score = summary_detail.get("total_score", 0)
    stars = summary_detail.get("stars", 1)
    rating_name = summary_detail.get("rating_name", "")
    risk_level = summary_detail.get("risk_level", "")
    main_color = summary_detail.get("color", "#dc2626")
    main_bg = _score_bg(total_score)
    position = summary_detail.get("position", "")
    ma10 = summary_detail.get("ma10")
    ma20 = summary_detail.get("ma20")
    highlights = summary_detail.get("highlights") or []
    risks = summary_detail.get("risks") or []

    # 短中长评级
    m06 = module_results.get("M06")
    tech = m06.detail if m06 else {}
    stance = tech.get("stance", "")

    short_label = "📈 买入" if total_score >= 70 else ("🔄 中性" if total_score >= 55 else "📉 回避")
    mid_label = "🟢 乐观" if total_score >= 72 else ("🟡 中性" if total_score >= 58 else "🔴 谨慎")
    long_label = "⭐ 价值" if total_score >= 78 else ("🔄 观察" if total_score >= 62 else "❌ 规避")

    # ── 首屏看板 ──
    dashboard = f"""
<div style="background:linear-gradient(135deg,#1e3a5f 0%,#1e40af 100%);
            border-radius:16px;padding:28px;margin-bottom:20px;color:#fff">
  <!-- 标题 -->
  <div style="text-align:center;margin-bottom:20px">
    <div style="font-size:0.9em;opacity:0.8;margin-bottom:4px">A股机构级全维度投资分析报告</div>
    <div style="font-size:1.5em;font-weight:800">{name}（{code}）</div>
    <div style="font-size:0.85em;opacity:0.75;margin-top:4px">
      {industry} · {board} · 报告时间：{fetch_time}
    </div>
  </div>

  <!-- 综合评分大卡 -->
  <div style="background:{main_bg};border-radius:12px;padding:20px;text-align:center;margin-bottom:16px">
    <div style="font-size:4em;font-weight:900;color:{main_color};line-height:1">{total_score:.0f}</div>
    <div style="font-size:1em;color:#374151;margin-top:4px">综合投资评分（满分100分）</div>
    <div style="margin-top:8px">
      <span style="color:#f59e0b;font-size:1.5em">{"★" * stars}{"☆" * (5 - stars)}</span>
      <span style="background:{main_color};color:#fff;padding:3px 12px;border-radius:20px;
                  font-size:0.85em;font-weight:700;margin-left:10px">{rating_name}</span>
    </div>
    <div style="margin-top:8px;color:{main_color};font-size:0.9em;font-weight:600">
      风险等级：{risk_level} · 建议仓位：{position}
    </div>
  </div>

  <!-- 两列信息 -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
    <div style="background:rgba(255,255,255,0.1);border-radius:8px;padding:12px">
      <div style="font-size:0.8em;opacity:0.8;margin-bottom:6px">📊 行情速览</div>
      <div style="font-size:1.3em;font-weight:700">{price:.2f} 元</div>
      <div style="font-size:0.9em;color:{"#4ade80" if pct > 0 else "#f87171"}">{pct:+.2f}%</div>
      <div style="font-size:0.8em;opacity:0.75;margin-top:4px">MA10:{ma10 or "N/A"} | MA20:{ma20 or "N/A"}</div>
    </div>
    <div style="background:rgba(255,255,255,0.1);border-radius:8px;padding:12px">
      <div style="font-size:0.8em;opacity:0.8;margin-bottom:6px">📅 三周期评级</div>
      <div style="font-size:0.9em;margin:3px 0">短线（1-7日）：<strong>{short_label}</strong></div>
      <div style="font-size:0.9em;margin:3px 0">中线（1-3月）：<strong>{mid_label}</strong></div>
      <div style="font-size:0.9em;margin:3px 0">长线（6-12月）：<strong>{long_label}</strong></div>
    </div>
  </div>

  <!-- 亮点与风险 -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
    <div style="background:rgba(21,128,61,0.25);border:1px solid rgba(74,222,128,0.4);
                border-radius:8px;padding:12px">
      <div style="font-size:0.8em;opacity:0.9;font-weight:700;margin-bottom:6px">✅ 核心投资亮点</div>
      {"".join(f'<div style="font-size:0.8em;margin:3px 0;opacity:0.95">• {h[:50]}</div>' for h in highlights[:3]) or '<div style="font-size:0.8em;opacity:0.7">暂无突出亮点</div>'}
    </div>
    <div style="background:rgba(220,38,38,0.2);border:1px solid rgba(248,113,113,0.4);
                border-radius:8px;padding:12px">
      <div style="font-size:0.8em;opacity:0.9;font-weight:700;margin-bottom:6px">⚠️ 核心风险提示</div>
      {"".join(f'<div style="font-size:0.8em;margin:3px 0;opacity:0.95">• {r[:50]}</div>' for r in risks[:3]) or '<div style="font-size:0.8em;opacity:0.7">无重大风险信号</div>'}
    </div>
  </div>

  <!-- 评分分项 -->
  <div style="background:rgba(255,255,255,0.08);border-radius:8px;padding:12px">
    <div style="font-size:0.8em;opacity:0.8;margin-bottom:8px;font-weight:600">各维度分项评分</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
"""

    # 添加分项评分
    dimension_groups = [
        ("基本面", ["M01", "M02", "M03"], "30%"),
        ("行业估值", ["M04", "M05"], "25%"),
        ("市场博弈", ["M06", "M07", "M08", "M09"], "25%"),
        ("风控催化", ["M10", "M11", "M12", "M13", "M14"], "20%"),
    ]

    for dim_name, mids, weight in dimension_groups:
        scores = [module_results[m].score for m in mids if m in module_results]
        avg = round(sum(scores) / len(scores) * 10, 1) if scores else 0
        bar_pct = int(avg)
        bar_color = _score_color(avg)
        dashboard += f"""
      <div style="background:rgba(255,255,255,0.1);border-radius:6px;padding:8px;text-align:center">
        <div style="font-size:0.75em;opacity:0.8">{dim_name}（{weight}）</div>
        <div style="font-size:1.3em;font-weight:800;color:#fff">{avg:.0f}<span style="font-size:0.6em">/100</span></div>
        <div style="background:rgba(255,255,255,0.2);border-radius:3px;height:4px;margin-top:4px">
          <div style="background:{bar_color};width:{bar_pct}%;height:4px;border-radius:3px"></div>
        </div>
      </div>"""

    dashboard += """
    </div>
  </div>
</div>
"""

    # ── 各模块卡片 ──
    modules_html = ""
    for mid in ["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08",
                "M09", "M10", "M11", "M12", "M13", "M14", "M15", "M16"]:
        result = module_results.get(mid)
        if result:
            modules_html += _module_card(result)

    # ── 完整 HTML ──
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{name}（{code}）投资分析报告 - {fetch_time[:10]}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                   "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background: #f3f4f6;
      margin: 0;
      padding: 16px;
      color: #111827;
      line-height: 1.6;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
    }}
    @media (max-width: 600px) {{
      .grid-2 {{ grid-template-columns: 1fr !important; }}
      .grid-4 {{ grid-template-columns: repeat(2,1fr) !important; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    {dashboard}
    <div style="margin-bottom:16px">
      <h2 style="color:#1e3a5f;font-size:1.1em;margin:0 0 4px;border-left:4px solid #1e40af;padding-left:10px">
        16大模块深度分析报告
      </h2>
      <div style="font-size:0.8em;color:#6b7280">每模块独立量化评分 × 加权汇总 = 综合得分</div>
    </div>
    {modules_html}
    <div style="background:#1e3a5f;color:#fff;border-radius:12px;padding:20px;text-align:center;margin-top:20px">
      <div style="font-weight:700;margin-bottom:8px">⚠️ 风险提示</div>
      <div style="font-size:0.85em;opacity:0.85;line-height:1.8">
        本分析基于公开市场数据与专业投研逻辑推演，仅为投资参考，不构成任何投资建议。<br>
        股市有风险，投资需谨慎。数据来源：东方财富、腾讯财经、新浪财经、AKShare。<br>
        报告生成时间：{fetch_time} | 技能版本：v3.5.0
      </div>
    </div>
  </div>
</body>
</html>"""

    return html
