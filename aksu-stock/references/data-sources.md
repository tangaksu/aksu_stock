# 数据源字段责任文档

## 概述

本文档明确每个数据字段由哪个数据源负责提供，以及备用数据源的顺序。  
主数据源：**AKShare==1.18.64**（需安装）  
备用数据源：腾讯财经、新浪财经、东方财富、同花顺（均为纯 HTTP 请求，无需安装额外库）

---

## 字段责任分配表

### 实时行情字段

| 字段 | Python键 | 主责数据源 | 备用顺序 | AKShare函数 / HTTP端点 |
|------|---------|-----------|---------|----------------------|
| 最新价 | `price` | 腾讯财经 | 新浪财经 → AKShare东方财富 | `qt.gtimg.cn/q={sym}` |
| 昨收价 | `prev_close` | 腾讯财经 | 新浪财经 → AKShare | `qt.gtimg.cn/q={sym}` |
| 今开 | `open` | 腾讯财经 | 新浪财经 | `qt.gtimg.cn/q={sym}` |
| 最高 | `high` | 腾讯财经 | 新浪财经 | `qt.gtimg.cn/q={sym}` |
| 最低 | `low` | 腾讯财经 | 新浪财经 | `qt.gtimg.cn/q={sym}` |
| 涨跌幅% | `pct_change` | 腾讯财经 | 新浪财经 | 计算：(price-prev_close)/prev_close×100 |
| 成交量 | `volume` | 腾讯财经 | 新浪财经 → AKShare | `qt.gtimg.cn/q={sym}` |
| 成交额 | `amount` | 腾讯财经 | 新浪财经 → AKShare | `qt.gtimg.cn/q={sym}` |
| 换手率% | `turnover_rate` | AKShare东方财富 | 腾讯财经 | `ak.stock_zh_a_spot_em()` |
| PE-TTM | `pe_ttm` | AKShare东方财富 | 腾讯财经 | `ak.stock_zh_a_spot_em()` |
| PB | `pb` | AKShare东方财富 | 腾讯财经 | `ak.stock_zh_a_spot_em()` |
| 总市值(亿) | `market_cap` | AKShare东方财富 | 腾讯财经 | `ak.stock_zh_a_spot_em()` |
| 流通市值(亿) | `circulate_cap` | AKShare东方财富 | 腾讯财经 | `ak.stock_zh_a_spot_em()` |
| 52周最高 | `week52_high` | AKShare历史K线 | — | `ak.stock_zh_a_hist()` |
| 52周最低 | `week52_low` | AKShare历史K线 | — | `ak.stock_zh_a_hist()` |
| 量比 | `volume_ratio` | AKShare东方财富 | — | `ak.stock_zh_a_spot_em()` 或计算 |
| 股票名称 | `name` | 腾讯财经 | AKShare | `qt.gtimg.cn/q={sym}` |
| 上市日期 | `list_date` | AKShare | — | `ak.stock_individual_info_em()` |

### 财务指标字段

| 字段 | Python键 | 主责数据源 | AKShare函数 |
|------|---------|-----------|------------|
| ROE% | `roe` | AKShare东方财富 | `ak.stock_financial_abstract_ths()` |
| 毛利率% | `gross_margin` | AKShare | `ak.stock_profit_sheet_by_report_em()` |
| 净利率% | `net_margin` | AKShare | `ak.stock_profit_sheet_by_report_em()` |
| 营收(亿) | `revenue` | AKShare | `ak.stock_profit_sheet_by_report_em()` |
| 营收同比% | `revenue_yoy` | AKShare | `ak.stock_profit_sheet_by_report_em()` |
| 归母净利润(亿) | `net_profit` | AKShare | `ak.stock_profit_sheet_by_report_em()` |
| 净利润同比% | `profit_yoy` | AKShare | `ak.stock_profit_sheet_by_report_em()` |
| 扣非净利润(亿) | `profit_deducted` | AKShare | `ak.stock_profit_sheet_by_report_em()` |
| EPS | `eps` | AKShare | `ak.stock_financial_abstract_ths()` |
| 每股净资产 | `bvps` | AKShare | `ak.stock_financial_abstract_ths()` |
| 资产负债率% | `debt_ratio` | AKShare | `ak.stock_balance_sheet_by_report_em()` |
| 经营现金流(亿) | `ocf` | AKShare | `ak.stock_cash_flow_sheet_by_report_em()` |
| 股息率% | `dividend_yield` | AKShare | `ak.stock_financial_abstract_ths()` |
| PEG | `peg` | 计算 | PE-TTM / 净利润增速 |
| PS | `ps` | AKShare | `ak.stock_zh_a_spot_em()` |
| EV/EBITDA | `ev_ebitda` | AKShare | — |

### 历史K线字段

| 字段 | Python键 | 主责数据源 | AKShare函数 |
|------|---------|-----------|------------|
| 日K线DataFrame | `kline_df` | AKShare | `ak.stock_zh_a_hist(symbol, period="daily", adjust="qfq")` |
| 周K线DataFrame | `kline_weekly` | AKShare | `ak.stock_zh_a_hist(symbol, period="weekly", adjust="qfq")` |
| 月K线DataFrame | `kline_monthly` | AKShare | `ak.stock_zh_a_hist(symbol, period="monthly", adjust="qfq")` |
| MA5/10/20/60/120 | `ma_*` | 计算（来自日K） | 基于kline_df计算 |
| RSI(14) | `rsi14` | 计算（来自日K） | 基于kline_df计算 |
| MACD DIF/DEA/柱 | `macd_*` | 计算（来自日K） | 基于kline_df计算 |
| KDJ K/D/J | `kdj_*` | 计算（来自日K） | 基于kline_df计算 |
| BOLL上/中/下 | `boll_*` | 计算（来自日K） | 基于kline_df计算 |

### 资金与筹码字段

| 字段 | Python键 | 主责数据源 | AKShare函数 |
|------|---------|-----------|------------|
| 主力净流入(万) | `main_net_inflow` | AKShare | `ak.stock_individual_fund_flow()` |
| 超大单净流入 | `super_large_inflow` | AKShare | `ak.stock_individual_fund_flow()` |
| 大单净流入 | `large_inflow` | AKShare | `ak.stock_individual_fund_flow()` |
| 北向资金净流入(亿) | `north_net_inflow` | AKShare | `ak.stock_hsgt_hist()` |
| 龙虎榜数据 | `dragon_tiger` | AKShare | `ak.stock_lhb_detail_em()` |

### 股东与治理字段

| 字段 | Python键 | 主责数据源 | AKShare函数 |
|------|---------|-----------|------------|
| 股东人数 | `holder_num` | AKShare | `ak.stock_zh_a_gdhs_detail_em()` |
| 股权质押比例% | `pledge_ratio` | AKShare | `ak.stock_gpzy_pledge_ratio_em()` |
| 前十大流通股东 | `top10_holders` | AKShare | `ak.stock_gdfx_free_top_10_em()` |
| 大股东增减持 | `insider_changes` | AKShare | `ak.stock_em_hsgt_board_hold()` |

### 机构研报字段

| 字段 | Python键 | 主责数据源 | AKShare函数 |
|------|---------|-----------|------------|
| 研报列表 | `research_reports` | AKShare | `ak.stock_research_report_em()` |
| 机构评级分布 | `analyst_ratings` | AKShare | `ak.stock_analyst_detail_em()` |
| 平均目标价 | `target_price` | AKShare | `ak.stock_analyst_detail_em()` |

### 行业数据字段

| 字段 | Python键 | 主责数据源 | AKShare函数 |
|------|---------|-----------|------------|
| 所属行业 | `industry` | AKShare | `ak.stock_individual_info_em()` |
| 行业成分股 | `industry_peers` | AKShare | `ak.stock_board_industry_cons_em()` |
| 行业平均PE | `industry_avg_pe` | AKShare | `ak.stock_board_industry_name_em()` |
| 概念标签 | `stock_concepts` | AKShare | `ak.stock_board_concept_name_em()` |

### 市场情绪字段

| 字段 | Python键 | 主责数据源 | AKShare函数 |
|------|---------|-----------|------------|
| 涨跌家数 | `market_breadth` | AKShare | `ak.stock_market_activity_legu()` |
| 涨停家数 | `limit_up_count` | AKShare | `ak.stock_zt_pool_em()` |
| 跌停家数 | `limit_down_count` | AKShare | `ak.stock_dt_pool_em()` |

---

## 降级策略

当某字段的所有数据源均失败时：
1. 对应字段值设为 `None`
2. 元数据 `_success: false` + `_message: "⚠️ 数据获取失败（已尝试：xxx）"`
3. HTML报告中该位置明确标注：⚠️ 数据获取失败，请手动查询
4. **不允许**以 "N/A"、"—"、0 静默填充

---

## 版本升级注意事项

升级 akshare 版本前必须：
1. 对照本文档检查所有 `AKShare函数` 列的函数是否仍存在且参数未变
2. 运行 `python3 -m unittest tests/test_data_collector.py` 确认无断裂
3. 重点检查返回 DataFrame 的列名是否变化（`最新价`、`涨跌幅` 等中文列名最易变）
4. 更新 `requirements.txt` 中的版本号与本文档中的 AKShare 版本标注
