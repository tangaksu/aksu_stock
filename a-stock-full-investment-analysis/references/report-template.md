# HTML 报告模板与质量检查清单

---

## 输出方式

**HTML 单文件**（零依赖，任何环境可打开）：
1. AI 生成填好内容的 HTML 文件 → 用户浏览器打开
2. Ctrl+P（Mac: Cmd+P）→ 打印机选"另存为PDF"
3. 设置：A4，边距最小，勾选"背景图形"

**命名格式**：`report_{代码}_{YYYY-MM-DD}.html`（如 `report_600519_2026-06-29.html`）

---

## HTML 模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{简称}（{代码}）投资分析报告 {YYYY-MM-DD}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;font-size:13px;color:#111827;background:#f3f4f6;line-height:1.6;padding:16px}
.container{max-width:900px;margin:0 auto}
:root{--navy:#1e3a5f;--blue:#1e40af;--green:#15803d;--red:#dc2626;--yellow:#ca8a04;--orange:#ea580c}

/* 首屏看板 */
.dashboard{background:linear-gradient(135deg,var(--navy) 0%,var(--blue) 100%);border-radius:16px;padding:28px;margin-bottom:20px;color:#fff}
.db-title{text-align:center;margin-bottom:20px}
.db-name{font-size:1.5em;font-weight:800}
.db-sub{font-size:0.85em;opacity:0.75;margin-top:4px}
.score-card{border-radius:12px;padding:20px;text-align:center;margin-bottom:16px}
.score-num{font-size:4em;font-weight:900;line-height:1}
.score-label{font-size:1em;color:#374151;margin-top:4px}
.stars{color:#f59e0b;font-size:1.5em;margin-top:8px}
.rating-badge{color:#fff;padding:3px 12px;border-radius:20px;font-size:0.85em;font-weight:700;margin-left:10px;display:inline-block}
.pos-risk{font-size:0.9em;font-weight:600;margin-top:8px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.info-box{background:rgba(255,255,255,0.1);border-radius:8px;padding:12px}
.info-box .label{font-size:0.8em;opacity:0.8;margin-bottom:6px}
.info-box .val{font-size:1.3em;font-weight:700}
.info-box .sub{font-size:0.8em;opacity:0.75;margin-top:4px}
.cycle-row{font-size:0.9em;margin:3px 0}
.highlight-box{background:rgba(21,128,61,0.25);border:1px solid rgba(74,222,128,0.4);border-radius:8px;padding:12px}
.risk-box{background:rgba(220,38,38,0.2);border:1px solid rgba(248,113,113,0.4);border-radius:8px;padding:12px}
.box-title{font-size:0.8em;opacity:0.9;font-weight:700;margin-bottom:6px}
.box-item{font-size:0.8em;margin:3px 0;opacity:0.95}
.dim-bar{background:rgba(255,255,255,0.08);border-radius:8px;padding:12px}
.dim-bar .dim-label{font-size:0.8em;opacity:0.8;margin-bottom:8px;font-weight:600}
.dim-item{background:rgba(255,255,255,0.1);border-radius:6px;padding:8px;text-align:center}
.dim-score{font-size:1.3em;font-weight:800;color:#fff}
.dim-name{font-size:0.75em;opacity:0.8}
.bar-bg{background:rgba(255,255,255,0.2);border-radius:3px;height:4px;margin-top:4px}
.bar-fill{height:4px;border-radius:3px}

/* 模块卡片 */
.section-title{color:var(--navy);font-size:1.1em;margin:0 0 4px;border-left:4px solid var(--blue);padding-left:10px;font-weight:700}
.section-sub{font-size:0.8em;color:#6b7280;margin-bottom:16px}
.module-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
.card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.card-id{background:var(--navy);color:#fff;font-size:0.75em;padding:2px 8px;border-radius:4px;font-weight:600;margin-right:8px}
.card-name{font-size:1.05em;font-weight:700;color:#111827}
.card-score{font-size:1.4em;font-weight:800;padding:4px 12px;border-radius:8px;display:inline-block}
.card-score span{font-size:0.6em}
.findings{list-style:none;padding:0;margin:0 0 12px}
.findings li{padding:6px 10px;margin:4px 0;border-radius:4px;font-size:0.88em;line-height:1.5}
.f-ok{background:#f0fdf4;border-left:3px solid #86efac;color:#15803d}
.f-warn{background:#fffbeb;border-left:3px solid #fcd34d;color:#b45309}
.f-alert{background:#fef2f2;border-left:3px solid #fca5a5;color:#dc2626}
.f-info{background:#eff6ff;border-left:3px solid #93c5fd;color:#1d4ed8}
.f-default{background:#f9fafb;border-left:3px solid #e5e7eb;color:#374151}
.f-section{list-style:none;border-top:1px dashed #e5e7eb;margin:4px 0;padding:4px 0;font-weight:600;color:#374151}
.advice-table{width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px;padding:10px 12px;margin-top:10px}
.advice-table td{padding:3px 8px 3px 0;font-size:0.85em;color:#374151}
.advice-table td:first-child{font-weight:600;color:#6b7280;font-size:0.8em;white-space:nowrap;vertical-align:top}
.conclusion{margin-top:10px;padding:8px 12px;border-radius:6px;font-size:0.88em;font-weight:600;border-left-width:3px;border-left-style:solid}
.no-data-note{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:12px;margin:4px 0;font-size:0.88em;color:#9a3412}

/* 底部 */
.footer{background:var(--navy);color:#fff;border-radius:12px;padding:20px;text-align:center;margin-top:20px}
.footer-title{font-weight:700;margin-bottom:8px}
.footer-text{font-size:0.85em;opacity:0.85;line-height:1.8}

@media(max-width:600px){.grid2,.grid4{grid-template-columns:1fr!important}}
@media print{body{background:#fff;padding:0}@page{size:A4;margin:12mm 10mm}table{page-break-inside:avoid}}
</style>
</head>
<body>
<div class="container">

<!-- ═══ 首屏评分看板 ═══ -->
<div class="dashboard">
  <div class="db-title">
    <div style="font-size:0.9em;opacity:0.8;margin-bottom:4px">A股机构级全维度投资分析报告 v4.0</div>
    <div class="db-name">{简称}（{代码}）</div>
    <div class="db-sub">{行业} · {上市板块} · 报告时间：{YYYY-MM-DD HH:MM}</div>
    <div class="db-sub" style="font-size:0.8em;margin-top:2px">
      数据来源：{实际使用的数据源列表，如"东方财富/AKShare/新浪财经"}
    </div>
  </div>

  <!-- 综合评分大卡 -->
  <div class="score-card" style="background:{主背景色};margin-bottom:16px">
    <div class="score-num" style="color:{主色}">{综合得分:.0f}</div>
    <div class="score-label">综合投资评分（满分100分）</div>
    <div class="stars">
      {"★" × 星级数}{"☆" × (5-星级数)}
      <span class="rating-badge" style="background:{主色}">{评级名称}</span>
    </div>
    <div class="pos-risk" style="color:{主色}">
      风险等级：{低/中/高} · 建议仓位：{X-X}%
    </div>
  </div>

  <!-- 行情 + 三周期 -->
  <div class="grid2" style="margin-bottom:16px">
    <div class="info-box">
      <div class="label">📊 行情速览（来源：{数据源}）</div>
      <div class="val">{最新价:.2f} 元</div>
      <div style="font-size:0.9em;color:{涨为#4ade80跌为#f87171}">{涨跌幅:+.2f}%（{涨跌额:+.2f}元）</div>
      <div class="sub">
        开盘{开盘:.2f} | 最高{最高:.2f} | 最低{最低:.2f}<br>
        MA10:{MA10值} | MA20:{MA20值}<br>
        数据时间：{行情数据时间}
      </div>
    </div>
    <div class="info-box">
      <div class="label">📅 三周期评级</div>
      <div class="cycle-row">短线（1-7日）：<strong>{📈 买入/🔄 中性/📉 回避}</strong></div>
      <div class="cycle-row">中线（1-3月）：<strong>{🟢 乐观/🟡 中性/🔴 谨慎}</strong></div>
      <div class="cycle-row">长线（6-12月）：<strong>{⭐ 价值/🔄 观察/❌ 规避}</strong></div>
    </div>
  </div>

  <!-- 亮点 + 风险 -->
  <div class="grid2" style="margin-bottom:16px">
    <div class="highlight-box">
      <div class="box-title">✅ 核心投资亮点</div>
      <div class="box-item">• {亮点1（最多50字）}</div>
      <div class="box-item">• {亮点2（最多50字）}</div>
      <div class="box-item">• {亮点3（最多50字）}</div>
    </div>
    <div class="risk-box">
      <div class="box-title">⚠️ 核心风险提示</div>
      <div class="box-item">• {风险1（最多50字）}</div>
      <div class="box-item">• {风险2（最多50字）}</div>
      <div class="box-item">• {风险3（最多50字）}</div>
    </div>
  </div>

  <!-- 分项评分 -->
  <div class="dim-bar">
    <div class="dim-label">各维度分项评分</div>
    <div class="grid4">
      <div class="dim-item">
        <div class="dim-name">基本面（30%）</div>
        <div class="dim-score">{基本面100分值:.0f}<span style="font-size:0.6em">/100</span></div>
        <div class="bar-bg"><div class="bar-fill" style="background:{基本面颜色};width:{基本面分}%"></div></div>
      </div>
      <div class="dim-item">
        <div class="dim-name">行业估值（25%）</div>
        <div class="dim-score">{行业估值100分值:.0f}<span style="font-size:0.6em">/100</span></div>
        <div class="bar-bg"><div class="bar-fill" style="background:{颜色};width:{分}%"></div></div>
      </div>
      <div class="dim-item">
        <div class="dim-name">市场博弈（25%）</div>
        <div class="dim-score">{市场博弈100分值:.0f}<span style="font-size:0.6em">/100</span></div>
        <div class="bar-bg"><div class="bar-fill" style="background:{颜色};width:{分}%"></div></div>
      </div>
      <div class="dim-item">
        <div class="dim-name">风控催化（20%）</div>
        <div class="dim-score">{风控催化100分值:.0f}<span style="font-size:0.6em">/100</span></div>
        <div class="bar-bg"><div class="bar-fill" style="background:{颜色};width:{分}%"></div></div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ 16大模块分析 ═══ -->
<h2 class="section-title">16大模块深度分析报告</h2>
<p class="section-sub">每模块独立量化评分 × 加权汇总 = 综合得分 ｜ 所有数值均来自实时采集数据</p>

<!-- ═══ M01 模块卡片（以下16张卡片结构相同，依次填入M01-M16数据） ═══ -->
<div class="module-card">
  <div class="card-header">
    <div>
      <span class="card-id">M01</span>
      <span class="card-name">公司基础与业务拆解</span>
    </div>
    <div style="text-align:right">
      <div class="card-score" style="background:{模块背景色};color:{模块颜色}">
        {M01分:.1f}<span>/10</span>
      </div>
      <div style="margin-top:2px;color:#f59e0b">{"★" × 星级}{"☆" × (5-星级)}</div>
    </div>
  </div>

  <!-- 关键发现列表 -->
  <ul class="findings">
    <!-- ✅ 开头 → class="f-ok"；⚠️ → "f-warn"；🚨 → "f-alert"；🔍/ℹ️ → "f-info"；普通 → "f-default"；--- 开头（分组标题）→ "f-section" -->
    <li class="f-default">公司全称：{全称}，股票代码：{代码}</li>
    <li class="f-default">所属行业：{行业}，上市板块：{板块}</li>
    <li class="f-default">上市时间：{上市日期}</li>
    <li class="f-default">主营业务：{主营描述，最多100字}...</li>
    <li class="f-default">总市值：{X}亿，流通市值：{X}亿（数据来源：{数据源}，时间：{数据时间}）</li>
    <li class="f-ok">✅ {大市值蓝筹/中市值/小市值判断及理由}</li>
    <!-- 若数据缺失，输出：-->
    <!-- <li class="f-warn">⚠️ 【主营业务】数据获取失败，已尝试所有数据源，建议访问：https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/Index?type=web&code={代码}</li> -->
  </ul>

  <!-- 短中长建议 -->
  <table class="advice-table">
    <tr><td>短线</td><td>{短线操作建议，具体到价格或条件}</td></tr>
    <tr><td>中线</td><td>{中线操作建议}</td></tr>
    <tr><td>长线</td><td>{长线操作建议}</td></tr>
  </table>

  <!-- 结论 -->
  <div class="conclusion" style="background:{模块背景色};color:{模块颜色};border-left-color:{模块颜色}">
    💡 {模块核心结论，一句话}
  </div>
</div>

<!-- M02-M15 的卡片结构与M01完全相同，依次填入对应模块数据 -->
<!-- 每张卡片的 key_findings 中，必须包含采集到的真实数值 -->
<!-- 若某模块的某个关键字段缺失，在findings中用 f-warn 标注 -->

<!-- 【M02-M15 卡片此处省略，格式与M01完全一致，按序填入】 -->

<!-- ═══ M16 综合总结（特殊样式） ═══ -->
<div class="module-card" style="border:2px solid var(--navy)">
  <div class="card-header">
    <div>
      <span class="card-id" style="background:#7c3aed">M16</span>
      <span class="card-name" style="font-size:1.15em">综合投资策略总结</span>
    </div>
    <div style="text-align:right">
      <div style="font-size:2em;font-weight:900;color:{主色}">{综合得分:.0f}<span style="font-size:0.4em">/100</span></div>
      <div style="color:#f59e0b;font-size:1.3em">{"★"×星级}{"☆"×(5-星级)}</div>
    </div>
  </div>

  <ul class="findings">
    <li class="f-section">--- 综合评分分解 ---</li>
    <li class="f-info">🔍 基本面（M01+M02+M03）均分：{X}/10，权重30%，贡献{X}分</li>
    <li class="f-info">🔍 行业估值（M04+M05）均分：{X}/10，权重25%，贡献{X}分</li>
    <li class="f-info">🔍 市场博弈（M06+M07+M08+M09）均分：{X}/10，权重25%，贡献{X}分</li>
    <li class="f-info">🔍 风控催化（M10+M11+M12+M13+M14）均分：{X}/10，权重20%，贡献{X}分</li>
    <li class="f-section">--- 核心亮点 ---</li>
    <li class="f-ok">✅ {亮点1}</li>
    <li class="f-ok">✅ {亮点2}</li>
    <li class="f-ok">✅ {亮点3}</li>
    <li class="f-section">--- 核心风险 ---</li>
    <li class="f-warn">⚠️ {风险1}</li>
    <li class="f-warn">⚠️ {风险2}</li>
    <li class="f-warn">⚠️ {风险3}</li>
    <li class="f-section">--- 操作建议（基于实时数据）---</li>
    <li class="f-default">入场区间：{X}-{X}元（基于MA10={X}）</li>
    <li class="f-default">止损位：{X}元（MA20={X}，损失约{X}%）</li>
    <li class="f-default">止盈目标：{X}元（+8%）/ {X}元（+15%）</li>
    <li class="f-default">持仓建议：{X-X}%仓位</li>
  </ul>

  <table class="advice-table">
    <tr><td>短线</td><td>{1-7日操作策略}</td></tr>
    <tr><td>中线</td><td>{1-3月操作策略}</td></tr>
    <tr><td>长线</td><td>{6-12月投资策略}</td></tr>
  </table>

  <div class="conclusion" style="background:{主背景色};color:{主色};border-left-color:{主色};font-size:1em;padding:12px">
    💡 {综合结论：一段话，包含评级、核心逻辑、操作建议}
  </div>
</div>

<!-- ═══ 底部风险提示 ═══ -->
<div class="footer">
  <div class="footer-title">⚠️ 重要风险提示</div>
  <div class="footer-text">
    本分析基于公开市场数据与专业投研逻辑推演，仅为投资参考，不构成任何投资建议。<br>
    数据来源：东方财富、AKShare、新浪财经、腾讯财经、同花顺、通用Web搜索。<br>
    股市有风险，投资需谨慎。报告生成时间：{YYYY-MM-DD HH:MM} | 技能版本：v4.0.0
  </div>
</div>

</div><!-- /container -->
</body>
</html>
```

---

## 颜色参考表

| 分值区间 | 主色 | 背景色 |
|---------|------|-------|
| ≥90 | #15803d | #dcfce7 |
| 80-89 | #16a34a | #d1fae5 |
| 70-79 | #ca8a04 | #fef9c3 |
| 60-69 | #ea580c | #ffedd5 |
| <60 | #dc2626 | #fee2e2 |

---

## 质量检查清单

```
【数据真实性】
□ 所有价格来自本次实时采集（非训练记忆），已标注数据时间和来源
□ 每个财务数字已标注报告期（如"2025Q3，截至2025-09-30"）
□ 量比已用采集值计算（今日成交量/近20日均量）
□ MA/RSI/MACD 数值来自K线数据，已标注计算来源
□ 行业对标数据来自采集（非推测），已列出具体对比标的

【字段完整性】
□ 若某字段采集失败：已在报告中明确标注⚠️并说明失败原因
□ 无静默的 N/A 或 — 填写（必须说明为何缺失）
□ 数据整理表（Step 2）中每个字段均已填写来源

【评分自洽】
□ M01-M15 各模块分值均在 1.0-10.0 之间
□ 综合评分计算公式已执行：(基本面×30%+行业估值×25%+市场博弈×25%+风控催化×20%)×10
□ 维度分项分值之和逻辑自洽（不出现维度分高但综合分低的异常）
□ 星级与分值对应正确（9-10=5星，8-9=4星，7-8=3星，5-7=3星，3-5=2星，1-3=1星）

【HTML 输出】
□ 无残留占位符 {xxx}（所有花括号内容已替换为真实值）
□ 颜色与评分等级对应正确（绿/黄/橙/红）
□ 单文件，无外部CSS/JS依赖
□ @media print 包含 @page {size:A4}

【财务数据特殊检查】
□ PE 异常值处理：若 PE < 0 或 PE > 5000，标注"PE不具参考意义（亏损或特殊情况）"
□ 科创板/北交所股票：涨跌幅限制为±20%（非±10%），在报告中标注
□ ST/退市风险股票：在报告封面显著标注，涨跌幅限制±5%
```

---

## 数据缺失时的统一提示格式

当某个字段所有6层数据源均无法获取时，使用以下标准提示（填入对应模块的 findings 中）：

```
⚠️ 【{字段名}】数据获取失败
  · 已尝试：东方财富页面fetch / AKShare接口 / 新浪财经 / 腾讯财经 / 同花顺 / Web搜索
  · 建议手动查询：{推荐URL，如 https://emweb.securities.eastmoney.com/PC_HSF10/...}
  · 影响：本模块评分维持基础分5.0，分析仅供参考
```
