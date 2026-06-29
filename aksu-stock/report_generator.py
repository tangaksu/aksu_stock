"""
report_generator.py — HTML 报告生成器
aksu-stock v5.1.5

输出：单文件 HTML，首屏双百分制看板置顶，17大模块卡片式布局。
无外部依赖，浏览器直接打开，支持 Ctrl+P 导出 PDF。
"""
from __future__ import annotations
from datetime import datetime
from typing import Any


# ─────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────

def _esc(s: Any) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt(v: Any, decimal: int = 2, suffix: str = "") -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{decimal}f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


def _pct(v: Any) -> str:
    return _fmt(v, 2, "%")


def _color_for_score(score: float, out_of_100: bool = True) -> str:
    """返回对应评分的 CSS 颜色变量名"""
    s = score if out_of_100 else score * 10
    if s >= 90:
        return "#1a7a4a"
    if s >= 80:
        return "#28a745"
    if s >= 70:
        return "#ffc107"
    if s >= 60:
        return "#fd7e14"
    return "#dc3545"


def _stars_html(stars: int) -> str:
    full = "★" * stars
    empty = "☆" * (5 - stars)
    return f'<span class="stars">{full}</span><span class="stars-empty">{empty}</span>'


def _badge(text: str, color: str = "#6c757d") -> str:
    return f'<span class="badge" style="background:{color}">{_esc(text)}</span>'


# ─────────────────────────────────────────────────────────
# CSS 样式
# ─────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
       background: #f5f7fa; color: #333; line-height: 1.6; font-size: 14px; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
/* ── 顶部看板 ── */
.dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
.score-card { background: #fff; border-radius: 16px; padding: 28px 24px; box-shadow: 0 4px 20px rgba(0,0,0,.1);
              display: flex; flex-direction: column; align-items: center; text-align: center; }
.score-card .score-big { font-size: 72px; font-weight: 900; line-height: 1; }
.score-card .score-label { font-size: 16px; font-weight: 700; margin-top: 6px; }
.score-card .score-sub { font-size: 13px; color: #666; margin-top: 4px; }
/* ── 速览区 ── */
.overview { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,.08); margin-bottom: 24px; }
.overview h2 { font-size: 16px; font-weight: 700; margin-bottom: 16px; color: #222; border-left: 4px solid #007bff; padding-left: 10px; }
.overview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
.overview-item { background: #f8f9fa; border-radius: 8px; padding: 10px 14px; }
.overview-item .label { font-size: 11px; color: #888; }
.overview-item .value { font-size: 16px; font-weight: 700; color: #222; }
/* ── 评级行 ── */
.rating-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 14px 0; }
.rating-item { background: #f0f4ff; border-radius: 10px; padding: 8px 16px; text-align: center; }
.rating-item .period { font-size: 11px; color: #777; }
.rating-item .rating { font-size: 14px; font-weight: 700; }
/* ── 亮点/风险区 ── */
.highlight-risk { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
.list-card { background: #fff; border-radius: 16px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
.list-card h3 { font-size: 14px; font-weight: 700; margin-bottom: 12px; }
.list-card ul { list-style: none; }
.list-card ul li { padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.list-card ul li:last-child { border-bottom: none; }
/* ── 模块卡片 ── */
.module-section { margin-bottom: 32px; }
.module-section h2 { font-size: 18px; font-weight: 700; color: #333; margin-bottom: 16px;
                     border-bottom: 2px solid #e9ecef; padding-bottom: 8px; }
.module-card { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,.08);
               margin-bottom: 16px; border-left: 5px solid #dee2e6; }
.module-card.score-high { border-left-color: #28a745; }
.module-card.score-mid  { border-left-color: #ffc107; }
.module-card.score-low  { border-left-color: #dc3545; }
.module-card.timing     { border-left-color: #6f42c1; }
.module-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.module-title { font-size: 16px; font-weight: 700; }
.module-score-box { display: flex; flex-direction: column; align-items: flex-end; }
.module-score { font-size: 28px; font-weight: 900; }
.module-stars { font-size: 16px; }
.module-findings ul { list-style: none; margin: 10px 0; }
.module-findings ul li { padding: 5px 0; font-size: 13px; border-bottom: 1px solid #f5f5f5; }
.module-findings ul li:last-child { border-bottom: none; }
.advice-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 14px; }
.advice-item { background: #f8f9fa; border-radius: 10px; padding: 10px 12px; }
.advice-item .period { font-size: 11px; color: #888; font-weight: 600; }
.advice-item .text { font-size: 12px; color: #444; margin-top: 4px; }
/* ── 择时模块特殊样式 ── */
.timing-dims { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 14px 0; }
.timing-dim { background: #f8f9fa; border-radius: 10px; padding: 10px; text-align: center; }
.timing-dim .dim-name { font-size: 11px; color: #777; }
.timing-dim .dim-score { font-size: 20px; font-weight: 800; }
.timing-dim .dim-max { font-size: 10px; color: #aaa; }
.timing-operation { background: #f0fff4; border: 1px solid #b7eb8f; border-radius: 10px;
                    padding: 14px 18px; font-size: 14px; font-weight: 700; margin: 14px 0; }
/* ── 对标表格 ── */
table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
th, td { padding: 8px 10px; text-align: right; border-bottom: 1px solid #f0f0f0; }
th { background: #f8f9fa; font-weight: 600; text-align: center; color: #555; }
td:first-child, th:first-child { text-align: left; }
tr:hover td { background: #fafafa; }
/* ── 综合总结 ── */
.summary-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               color: #fff; border-radius: 16px; padding: 28px; margin-bottom: 24px; }
.summary-box h2 { font-size: 20px; margin-bottom: 20px; }
.summary-params { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.summary-param { background: rgba(255,255,255,.15); border-radius: 10px; padding: 12px 16px; }
.summary-param .sp-label { font-size: 11px; opacity: .8; }
.summary-param .sp-value { font-size: 18px; font-weight: 700; }
/* ── 风险提示 ── */
.risk-footer { background: #fff3cd; border: 1px solid #ffc107; border-radius: 12px; padding: 16px 20px; margin-top: 24px; font-size: 12px; color: #856404; }
/* ── 徽章 ── */
.badge { display: inline-block; padding: 2px 8px; border-radius: 20px; color: #fff; font-size: 11px; font-weight: 600; margin: 2px; }
.stars { color: #ffc107; }
.stars-empty { color: #ddd; }
/* ── 响应式 ── */
@media (max-width: 768px) {
  .dashboard { grid-template-columns: 1fr; }
  .advice-grid { grid-template-columns: 1fr; }
  .timing-dims { grid-template-columns: repeat(3, 1fr); }
  .highlight-risk { grid-template-columns: 1fr; }
  .summary-params { grid-template-columns: 1fr; }
}
@media print {
  body { background: #fff; }
  .container { max-width: 100%; padding: 10px; }
  .module-card { break-inside: avoid; }
}
"""


# ─────────────────────────────────────────────────────────
# 首屏双评分看板
# ─────────────────────────────────────────────────────────

def _render_dashboard(data: dict, d17: Any, d16: Any) -> str:
    ts = d17.detail.get("total_score", 0) if d17 else 0
    tl = d16.detail.get("timing_score", 0) if d16 else 0
    stars = d17.detail.get("stars", 1) if d17 else 1
    rating_name = d17.detail.get("rating_name", "—") if d17 else "—"
    timing_level = d16.detail.get("timing_level", "—") if d16 else "—"
    rc = _color_for_score(ts)
    tc = _color_for_score(tl)
    position = d17.detail.get("position", "—") if d17 else "—"

    return f"""
<div class="dashboard">
  <div class="score-card">
    <div style="font-size:13px;color:#888;margin-bottom:8px">📊 综合投资价值评分</div>
    <div class="score-big" style="color:{rc}">{ts:.1f}</div>
    <div class="score-label" style="color:{rc}">{_stars_html(stars)} {_esc(rating_name)}</div>
    <div class="score-sub">建议仓位：{_esc(position)}</div>
    <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;justify-content:center">
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 12px">
        <div style="font-size:10px;color:#888">基本面</div>
        <div style="font-size:16px;font-weight:700">{d17.detail['dim_scores']['基本面']*10:.0f}</div>
      </div>
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 12px">
        <div style="font-size:10px;color:#888">行业估值</div>
        <div style="font-size:16px;font-weight:700">{d17.detail['dim_scores']['行业估值']*10:.0f}</div>
      </div>
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 12px">
        <div style="font-size:10px;color:#888">市场博弈</div>
        <div style="font-size:16px;font-weight:700">{d17.detail['dim_scores']['市场博弈']*10:.0f}</div>
      </div>
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 12px">
        <div style="font-size:10px;color:#888">风控催化</div>
        <div style="font-size:16px;font-weight:700">{d17.detail['dim_scores']['风控催化']*10:.0f}</div>
      </div>
    </div>
  </div>
  <div class="score-card">
    <div style="font-size:13px;color:#888;margin-bottom:8px">⚡ 现价交易择时评分</div>
    <div class="score-big" style="color:{tc}">{tl:.1f}</div>
    <div class="score-label" style="color:{tc}">{_esc(timing_level)}</div>
    <div class="score-sub">{_esc(d16.detail.get('operation', '—') if d16 else '—')}</div>
    <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;justify-content:center">
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 10px">
        <div style="font-size:10px;color:#888">技术/30</div>
        <div style="font-size:16px;font-weight:700">{d16.detail.get('dim1_technical',0) if d16 else '—'}</div>
      </div>
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 10px">
        <div style="font-size:10px;color:#888">估值/25</div>
        <div style="font-size:16px;font-weight:700">{d16.detail.get('dim2_valuation',0) if d16 else '—'}</div>
      </div>
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 10px">
        <div style="font-size:10px;color:#888">资金/20</div>
        <div style="font-size:16px;font-weight:700">{d16.detail.get('dim3_capital',0) if d16 else '—'}</div>
      </div>
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 10px">
        <div style="font-size:10px;color:#888">情绪/15</div>
        <div style="font-size:16px;font-weight:700">{d16.detail.get('dim4_sentiment',0) if d16 else '—'}</div>
      </div>
      <div style="text-align:center;background:#f8f9fa;border-radius:8px;padding:6px 10px">
        <div style="font-size:10px;color:#888">盈亏/10</div>
        <div style="font-size:16px;font-weight:700">{d16.detail.get('dim5_riskReward',0) if d16 else '—'}</div>
      </div>
    </div>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────
# 核心信息速览
# ─────────────────────────────────────────────────────────

def _render_overview(data: dict, d17: Any, d14: Any) -> str:
    code = data.get("code", "")
    name = data.get("name") or code
    price = data.get("price")
    pct = data.get("pct_change")
    pe_ttm = data.get("pe_ttm")
    pb = data.get("pb")
    market_cap = data.get("market_cap")
    industry = data.get("industry", "—")
    list_date = data.get("list_date", "—")
    turnover = data.get("turnover_rate")
    amount = data.get("amount")
    week52_position = data.get("week52_position")
    pct_color = "#dc3545" if (pct or 0) < 0 else "#28a745"
    highlights = d17.detail.get("highlights", []) if d17 else []
    risks = d17.detail.get("core_risks", []) if d17 else []
    stop = d14.detail.get("stop_loss") if d14 else None
    tp1 = d14.detail.get("take_profit_1") if d14 else None
    rr = d14.detail.get("risk_reward") if d14 else None

    return f"""
<div class="overview">
  <h2>📋 核心信息速览</h2>
  <div class="overview-grid">
    <div class="overview-item">
      <div class="label">股票代码/名称</div>
      <div class="value">{_esc(code)} / {_esc(name)}</div>
    </div>
    <div class="overview-item">
      <div class="label">最新价 / 涨跌幅</div>
      <div class="value" style="color:{pct_color}">{_fmt(price)} / {_pct(pct)}</div>
    </div>
    <div class="overview-item">
      <div class="label">所属行业</div>
      <div class="value">{_esc(industry)}</div>
    </div>
    <div class="overview-item">
      <div class="label">总市值</div>
      <div class="value">{_fmt((market_cap or 0)/1e8, 1, "亿") if market_cap else "—"}</div>
    </div>
    <div class="overview-item">
      <div class="label">PE-TTM / PB</div>
      <div class="value">{_fmt(pe_ttm, 1)}x / {_fmt(pb, 2)}x</div>
    </div>
    <div class="overview-item">
      <div class="label">换手率 / 成交额</div>
      <div class="value">{_pct(turnover)} / {_fmt((amount or 0)/1e8, 2, "亿") if amount else "—"}</div>
    </div>
    <div class="overview-item">
      <div class="label">52周位置</div>
      <div class="value">{_fmt(week52_position, 1, "%")}</div>
    </div>
    <div class="overview-item">
      <div class="label">上市日期</div>
      <div class="value">{_esc(str(list_date or "—"))}</div>
    </div>
    <div class="overview-item">
      <div class="label">止损 / 止盈1</div>
      <div class="value" style="color:#dc3545">{_fmt(stop)} / {_fmt(tp1)}</div>
    </div>
    <div class="overview-item">
      <div class="label">盈亏比</div>
      <div class="value">{_fmt(rr, 1)}:1</div>
    </div>
  </div>
</div>
<div class="highlight-risk">
  <div class="list-card">
    <h3 style="color:#28a745">✅ 核心投资亮点</h3>
    <ul>{"".join(f'<li>• {_esc(h)}</li>' for h in (highlights or ["暂无明显亮点"]))}</ul>
  </div>
  <div class="list-card">
    <h3 style="color:#dc3545">⚠️ 核心风险提示</h3>
    <ul>{"".join(f'<li>• {_esc(r)}</li>' for r in (risks or ["暂无重大风险"]))}</ul>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────
# 单个模块卡片
# ─────────────────────────────────────────────────────────

def _score_class(score: float) -> str:
    if score >= 7:
        return "score-high"
    if score >= 4:
        return "score-mid"
    return "score-low"


def _render_module_card(r: Any) -> str:
    color = _color_for_score(r.score, out_of_100=False)
    findings_html = "".join(f"<li>• {_esc(f)}</li>" for f in (r.key_findings or []))
    return f"""
<div class="module-card {_score_class(r.score)}">
  <div class="module-header">
    <div>
      <div class="module-title">{_esc(r.module_id)} — {_esc(r.module_name)}</div>
      <div style="margin-top:4px">{_stars_html(r.stars)}</div>
    </div>
    <div class="module-score-box">
      <div class="module-score" style="color:{color}">{r.score:.1f}</div>
      <div style="font-size:11px;color:#aaa">/ 10分</div>
    </div>
  </div>
  <div class="module-findings"><ul>{findings_html}</ul></div>
  <div class="advice-grid">
    <div class="advice-item">
      <div class="period">⚡ 短线（1-7日）</div>
      <div class="text">{_esc(r.short_advice or "—")}</div>
    </div>
    <div class="advice-item">
      <div class="period">📅 中线（1-3月）</div>
      <div class="text">{_esc(r.mid_advice or "—")}</div>
    </div>
    <div class="advice-item">
      <div class="period">🗓 长线（6-12月）</div>
      <div class="text">{_esc(r.long_advice or "—")}</div>
    </div>
  </div>
  <div style="margin-top:10px;font-size:13px;font-weight:600;color:{color}">
    💡 结论：{_esc(r.conclusion or "—")}
  </div>
</div>"""


# ─────────────────────────────────────────────────────────
# M16 择时模块特殊渲染
# ─────────────────────────────────────────────────────────

def _render_m16_card(r: Any) -> str:
    d = r.detail
    ts = d.get("timing_score", 0)
    tl = d.get("timing_level", "—")
    tc = _color_for_score(ts)
    op = d.get("operation", "—")
    dims = [
        ("技术面", d.get("dim1_technical", 0), 30),
        ("估值性价比", d.get("dim2_valuation", 0), 25),
        ("资金承接", d.get("dim3_capital", 0), 20),
        ("情绪催化", d.get("dim4_sentiment", 0), 15),
        ("盈亏比", d.get("dim5_riskReward", 0), 10),
    ]
    dims_html = "".join(f"""
      <div class="timing-dim">
        <div class="dim-name">{_esc(name)}</div>
        <div class="dim-score" style="color:{_color_for_score(score/max_s*100)}">{score:.1f}</div>
        <div class="dim-max">/{max_s}</div>
      </div>""" for name, score, max_s in dims)
    findings_html = "".join(f"<li>• {_esc(f)}</li>" for f in (r.key_findings or []))
    sl = d.get("stop_loss")
    tg = d.get("target")
    return f"""
<div class="module-card timing">
  <div class="module-header">
    <div>
      <div class="module-title">M16 — 现价交易择时评分 <span class="badge" style="background:#6f42c1">独立100分制</span></div>
    </div>
    <div class="module-score-box">
      <div style="font-size:48px;font-weight:900;color:{tc};line-height:1">{ts:.1f}</div>
      <div style="font-size:12px;color:{tc};font-weight:700">{_esc(tl)}</div>
      <div style="font-size:10px;color:#aaa">/ 100分</div>
    </div>
  </div>
  <div class="timing-dims">{dims_html}</div>
  <div class="timing-operation" style="border-color:{tc};background:{tc}15;color:{tc}">{_esc(op)}</div>
  <div class="module-findings"><ul>{findings_html}</ul></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
    <div style="background:#fff5f5;border-radius:8px;padding:10px">
      <div style="font-size:11px;color:#888">🛑 止损位</div>
      <div style="font-size:20px;font-weight:800;color:#dc3545">{_fmt(sl)}</div>
    </div>
    <div style="background:#f0fff4;border-radius:8px;padding:10px">
      <div style="font-size:11px;color:#888">🎯 目标价</div>
      <div style="font-size:20px;font-weight:800;color:#28a745">{_fmt(tg)}</div>
    </div>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────
# M17 综合总结特殊渲染
# ─────────────────────────────────────────────────────────

def _render_m17_card(r: Any) -> str:
    d = r.detail
    ts = d.get("total_score", 0)
    rc = _color_for_score(ts)
    timing_score = d.get("timing_score", 0)
    tc = _color_for_score(timing_score)
    comparison_rows = d.get("comparison_rows", [])

    table_html = ""
    if comparison_rows:
        rows_html = ""
        for row in comparison_rows[:5]:
            pct = row.get("pct_change") or 0
            pct_c = "#dc3545" if pct < 0 else "#28a745"
            rows_html += f"""<tr>
              <td>{_esc(row.get('name',''))}<br><small style="color:#999">{_esc(row.get('code',''))}</small></td>
              <td>{_fmt(row.get('price'))}</td>
              <td style="color:{pct_c}">{_pct(row.get('pct_change'))}</td>
              <td>{_fmt(row.get('pe_ttm'),1)}x</td>
              <td>{_fmt(row.get('market_cap_yi'),0)}亿</td>
            </tr>"""
        table_html = f"""
        <table>
          <thead><tr><th>对标标的</th><th>现价</th><th>涨跌%</th><th>PE-TTM</th><th>总市值</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>"""

    params_html = f"""
    <div class="summary-params">
      <div class="summary-param">
        <div class="sp-label">最优入场区间</div>
        <div class="sp-value">{_fmt(d['stop_loss']*1.005 if d.get('stop_loss') is not None else None, 2)} ~ {_fmt(d['stop_loss']*1.025 if d.get('stop_loss') is not None else None, 2)}</div>
      </div>
      <div class="summary-param">
        <div class="sp-label">强制止损位</div>
        <div class="sp-value">{_fmt(d.get('stop_loss'))}</div>
      </div>
      <div class="summary-param">
        <div class="sp-label">止盈目标1（减半仓）</div>
        <div class="sp-value">{_fmt(d.get('take_profit_1'))}</div>
      </div>
      <div class="summary-param">
        <div class="sp-label">止盈目标2（清仓）</div>
        <div class="sp-value">{_fmt(d.get('take_profit_2'))}</div>
      </div>
      <div class="summary-param">
        <div class="sp-label">建议仓位</div>
        <div class="sp-value">{_esc(d.get('position','—'))}</div>
      </div>
      <div class="summary-param">
        <div class="sp-label">盈亏比</div>
        <div class="sp-value">{_fmt(d.get('risk_reward'),1)}:1</div>
      </div>
    </div>"""

    tracking_html = f"""
    <div style="background:rgba(255,255,255,.1);border-radius:10px;padding:16px;margin-top:14px">
      <div style="font-weight:700;margin-bottom:10px">📌 动态持仓跟踪方案</div>
      <div style="font-size:13px;line-height:1.8">
        📈 {_esc(d.get('add_condition','—'))}<br>
        🛑 {_esc(d.get('stop_condition','—'))}<br>
        💰 {_esc(d.get('profit_condition','—'))}<br>
        🔄 {_esc(d.get('swing_condition','—'))}
      </div>
    </div>"""

    warning = d.get("leverage_warning", "")
    warning_html = f'<div style="background:#dc3545;border-radius:8px;padding:10px;margin-top:12px;font-size:13px">{_esc(warning)}</div>' if warning else ""

    substitutes = d.get("substitutes", "")

    return f"""
<div class="summary-box">
  <h2>M17 — 多维加权综合投资策略总结</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
    <div style="text-align:center">
      <div style="font-size:12px;opacity:.8">综合投资价值</div>
      <div style="font-size:64px;font-weight:900;color:{rc}">{ts:.1f}</div>
      <div style="font-size:14px;font-weight:700;color:{rc}">{_stars_html(d.get('stars',1))} {_esc(d.get('rating_name','—'))}</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:12px;opacity:.8">现价交易择时</div>
      <div style="font-size:64px;font-weight:900;color:{tc}">{timing_score:.1f}</div>
      <div style="font-size:14px;font-weight:700;color:{tc}">{_esc(d.get('timing_level','—'))}</div>
    </div>
  </div>
  {params_html}
  {tracking_html}
  {warning_html}
  {f'<div style="margin-top:12px;font-size:13px;background:rgba(255,255,255,.1);border-radius:8px;padding:12px">💡 同业替代参考：{_esc(substitutes)}</div>' if substitutes else ""}
</div>
{f'<div class="overview"><h2>同业对标数据</h2>{table_html}</div>' if table_html else ""}"""


# ─────────────────────────────────────────────────────────
# 主渲染函数
# ─────────────────────────────────────────────────────────

def generate_report(data: dict, module_results: dict) -> str:
    code = data.get("code", "")
    name = data.get("name") or code
    price = data.get("price")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    d17 = module_results.get("M17")
    d16 = module_results.get("M16")
    d14 = module_results.get("M14")

    # 模块分组
    groups = [
        ("基本面分析", ["M01", "M02", "M03"]),
        ("行业与估值", ["M04", "M05"]),
        ("市场博弈", ["M06", "M07", "M08", "M09"]),
        ("风控与催化", ["M10", "M11", "M12", "M13", "M14"]),
        ("同业对标", ["M15"]),
    ]

    modules_html = ""
    for section_name, mids in groups:
        cards_html = ""
        for mid in mids:
            r = module_results.get(mid)
            if r:
                cards_html += _render_module_card(r)
        if cards_html:
            modules_html += f'<div class="module-section"><h2>{section_name}</h2>{cards_html}</div>'

    # M16 独立渲染
    r16 = module_results.get("M16")
    if r16:
        modules_html += f'<div class="module-section"><h2>⚡ 现价交易择时（独立评分）</h2>{_render_m16_card(r16)}</div>'

    # 数据采集状态
    meta = data.get("_meta") or {}
    failed_fields = [k for k, v in meta.items() if not v.get("success")]
    audit_html = ""
    if failed_fields:
        audit_html = f"""
<div style="background:#fff3cd;border-radius:12px;padding:16px;margin-bottom:24px">
  <strong>📋 数据采集审计</strong>（以下字段获取失败，分析结果已降级处理）<br>
  <span style="color:#856404">{_esc(", ".join(failed_fields[:20]))}</span>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(name)}（{_esc(code)}）投资分析报告 — {now}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <div style="text-align:center;padding:20px 0 24px">
    <h1 style="font-size:24px;font-weight:900;color:#222">{_esc(name)} <span style="color:#888;font-size:18px">（{_esc(code)}）</span></h1>
    <p style="color:#888;font-size:13px">生成时间：{now} ｜ 现价：{_fmt(price)} ｜ 数据来源：AKShare 1.18.64 + 腾讯财经/新浪财经</p>
  </div>
  {_render_dashboard(data, d17, d16)}
  {_render_overview(data, d17, d14)}
  {audit_html}
  {_render_m17_card(d17) if d17 else ""}
  {modules_html}
  <div class="risk-footer">
    <strong>【风险提示】</strong> 本分析基于公开市场数据与专业投研逻辑推演，仅为投资参考，不构成任何投资建议。
    股市有风险，投资需谨慎。所有数据来源：AKShare 1.18.64、腾讯财经、新浪财经、东方财富、同花顺。
    分析结论存在局限性，请结合自身风险承受能力决策。
  </div>
</div>
</body>
</html>"""
    return html
