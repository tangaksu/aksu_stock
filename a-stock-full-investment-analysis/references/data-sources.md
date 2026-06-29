# 数据源与采集规范

> **核心原则**：所有数值必须从以下数据源采集，禁止凭记忆或推测填写任何数据。  
> 每个数据字段必须注明来源和数据时间。

---

## 交易所前缀规则

| 代码开头 | 前缀 | 示例 |
|---------|------|------|
| 60、68、90 | sh | sh600519 |
| 其余（00、30、002 等） | sz | sz000858 |

---

## 数据源 S1 — 东方财富（EastMoney）【最高优先级】

### S1-A：实时行情

**fetch URL（优先）**：
```
https://quote.eastmoney.com/{sh/sz}{代码}.html
示例：https://quote.eastmoney.com/sh600519.html
```

**搜索词（fetch失败时）**：
```
"{股票简称} {代码} 东方财富 实时行情 今日"
```

**提取字段**：
| 字段 | 位置/标识 | 示例 |
|------|-----------|------|
| 最新价 | 大字价格 | 1580.00 |
| 涨跌幅 | 价格旁 % | +1.23% |
| 涨跌额 | 价格旁 | +19.12 |
| 昨收 | 昨收/前收 | 1560.88 |
| 开盘 | 今开 | 1565.00 |
| 最高 | 最高 | 1592.00 |
| 最低 | 最低 | 1558.00 |
| 成交量 | 成交量 | 4.01万手 |
| 成交额 | 成交额 | 63.21亿 |
| 换手率 | 换手率 | 0.32% |
| 52周高 | 52周高/最高 | — |
| 52周低 | 52周低/最低 | — |
| 总市值 | 总市值 | 19868亿 |
| 流通市值 | 流通市值 | — |
| PE-TTM | 市盈率(TTM) | 28.5 |
| PB | 市净率 | 10.2 |
| 股息率 | 股息率 | 1.2% |
| 每股净资产 | 每股净资产 | — |
| 总股本 | 总股本 | 12.56亿股 |

### S1-B：K线历史数据

**fetch URL**：
```
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={1若sh/0若sz}.{代码}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&lmt=120&fqt=1&klt=101&beg=0&end=20500101
```
返回 JSON，`data.klines` 数组，每条格式：`日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率`

**搜索词（fetch失败时）**：
```
"{股票简称} {代码} 日K线 前复权 近120日"
```

### S1-C：财务数据

**主营业务/基础信息 fetch**：
```
https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/Index?type=web&code={sh/sz}{代码}
```
提取：公司简称、所属行业、上市时间、主营业务描述

**财务指标 fetch**：
```
https://emweb.securities.eastmoney.com/PC_HSF10/FinancialAnalysis/Index?type=web&code={sh/sz}{代码}
```
提取：ROE、毛利率、净利率、资产负债率、流动比率

**利润表 fetch**：
```
https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code={sh/sz}{代码}
```
提取：近5期营收、净利润、扣非净利润、营收同比、利润同比

**搜索词（fetch失败时）**：
```
搜索词 C1："{股票简称} {代码} 三季报/年报 营收 净利润 同比 {YYYY年}"
搜索词 C2："{股票简称} {代码} ROE 毛利率 净利率 资产负债率 财务数据"
搜索词 C3："{股票简称} {代码} 扣非净利润 经营现金流 {YYYY年}"
```

### S1-D：资金流向

**fetch URL**：
```
https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?secid={1若sh/0若sz}.{代码}&ut=b2884a393a59ad64002292a3e90d46a5&lmt=30&klt=1&fields1=f1%2Cf2%2Cf3%2Cf7&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf62%2Cf63
```
返回近30日每日：主力净流入、超大单净流入、大单净流入、中单净流入、小单净流入

**搜索词（fetch失败时）**：
```
"{股票简称} {代码} 主力净流入 资金流向 近5日 {YYYY年M月}"
```

### S1-E：股东与治理数据

**流通股东 fetch**：
```
https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/Index?type=web&code={sh/sz}{代码}
```
提取：前10大流通股东、持股比例、持股变动

**股东人数 fetch**：
```
https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_EH_SHAREHOLDERNUM&columns=TOTAL_HOLDER_NUM%2CCHANGE_RATIO%2CHOLDER_DATE&filter=(SECURITY_CODE%3D%22{代码}%22)&sortColumns=HOLDER_DATE&sortTypes=-1&pageSize=4
```
提取：最新/前期股东人数、变化比例

**质押情况 搜索**：
```
"{股票简称} {代码} 股权质押 质押比例 {YYYY年}"
```

**高管增减持 搜索**：
```
"{股票简称} {代码} 高管 增持 减持 {YYYY年}"
```

### S1-F：研究报告与机构评级

**研报列表 fetch**：
```
https://reportapi.eastmoney.com/report/list?cb=datatable&industryCode=*&pageSize=10&industry=*&rating=&ratingChange=&beginTime=&endTime=&pageNo=1&fields=&qType=0&orgCode=&code={代码}
```
提取：研报标题、机构、评级、目标价、日期

**搜索词（fetch失败时）**：
```
"{股票简称} {代码} 研究报告 评级 目标价 {YYYY年}"
"{股票简称} {代码} 买入 增持 机构评级 {近6个月}"
```

### S1-G：龙虎榜

**搜索词**：
```
"{股票简称} {代码} 龙虎榜 {YYYY年M月}"
```
提取：上榜原因、买卖前5席位净额、是否有机构席位

### S1-H：行业板块数据

**行业成分股 fetch**：
```
https://push2.eastmoney.com/api/qt/clist/get?cb=&pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=b:{行业板块代码}&fields=f2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2Cf14%2Cf15%2Cf16%2Cf17%2Cf18%2Cf20%2Cf21%2Cf23%2Cf24%2Cf25%2Cf22%2Cf11%2Cf62%2Cf128%2Cf136%2Cf115%2Cf152
```

**搜索词（fetch失败时）**：
```
"{行业名称} 板块 今日 涨跌幅 PE PB 行业均值 东方财富"
"{股票简称} {代码} 同行业 对标公司 竞争对手 PE对比"
```

---

## 数据源 S2 — AKShare【第二优先级】

> AKShare 为 Python 库，需要通过代码或工具调用。如果运行环境支持 Python，优先使用。

### S2-A：关键 AKShare 函数

```python
# 实时行情
akshare.stock_zh_a_spot_em()                    # A股实时行情（东财源）
akshare.stock_individual_info_em(symbol=code)   # 个股基础信息

# K线
akshare.stock_zh_a_hist(symbol=code, period="daily", start_date="...", end_date="...", adjust="qfq")

# 财务
akshare.stock_financial_analysis_indicator(symbol=code, start_year="2020")  # 财务指标
akshare.stock_profit_sheet_by_report_em(symbol=code)       # 利润表（季报）
akshare.stock_profit_sheet_by_yearly_em(symbol=code)       # 利润表（年报）
akshare.stock_balance_sheet_by_report_em(symbol=code)      # 资产负债表
akshare.stock_cash_flow_sheet_by_report_em(symbol=code)    # 现金流量表

# 股东
akshare.stock_circulate_stockholder_details(symbol=code)   # 流通股东
akshare.stock_holder_num_em(symbol=code)                   # 股东人数
akshare.stock_em_hold_change_detail(symbol=code)           # 高管增减持
akshare.stock_pledge_stat_em(symbol=code)                  # 股权质押

# 资金
akshare.stock_individual_fund_flow(stock=code, market="sh"/"sz")  # 个股资金流向（近30日）
akshare.stock_market_fund_flow()                           # 大盘资金流

# 行业
akshare.stock_board_industry_cons_em(symbol=行业名)        # 行业成分股
akshare.stock_board_industry_name_em()                     # 所有行业板块列表

# 机构
akshare.stock_research_report_em(symbol=code)              # 研究报告
```

### S2-B：AKShare 调用失败处理

若 AKShare 调用抛出异常或返回空，立即切换到 S3（新浪财经）。

---

## 数据源 S3 — 新浪财经（Sina Finance）【第三优先级】

### S3-A：实时行情

**fetch URL**：
```
https://hq.sinajs.cn/list={sh/sz}{代码}
示例：https://hq.sinajs.cn/list=sh600519
```
返回格式（CSV）：`名称,开盘,昨收,当前价,最高,最低,买1价,卖1价,成交量,成交额,买1量,买1价,...,日期,时间`

**备用 fetch**：
```
https://finance.sina.com.cn/realstock/company/{sh/sz}{代码}/nc.shtml
```

### S3-B：财务公告搜索

```
搜索词 1："{股票简称} {代码} 新浪财经 三季报/年报 营收 净利润"
搜索词 2："{股票简称} 机构评级 研报 site:finance.sina.com.cn"
```

### S3-C：重大公告

```
https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_Bulletin/stockid/{代码}/page_type/ndbg.phtml
```
提取：近3个月重大公告标题、日期

---

## 数据源 S4 — 腾讯财经（Tencent Finance）【第四优先级】

### S4-A：实时行情

**fetch URL**：
```
https://qt.gtimg.cn/q={sh/sz}{代码}
示例：https://qt.gtimg.cn/q=sh600519
```
返回 `~` 分隔字符串，字段顺序：
`[0]前缀, [1]名称, [2]代码, [3]当前价, [4]昨收, [5]开盘, [6]成交量(手), [7]外盘量, [8]内盘量, [9-18]五档买卖, [19-28]续..., [29]成交额, [30]BID1..., [31]涨跌幅, [32]当日涨跌, [33]最高, [34]最低, [35]52周高, [36]52周低, [37]成交额(万), [38]换手率, [39]PE(TTM), [40]..., [41]振幅, [42]流通市值, [43]总市值, [44]市净率, [45]..., [46]PB, [47]..., [48]..., [49]行业`

### S4-B：历史K线（备用）

**fetch URL**：
```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={sh/sz}{代码},day,,,120,qfq
```
返回 JSON，`data.{前缀代码}.qfqday` 数组，每条：`[日期, 开盘, 收盘, 最高, 最低, 成交量]`

---

## 数据源 S5 — 同花顺（THS）【第五优先级】

### S5-A：个股页面

**fetch URL**：
```
https://stockpage.10jqka.com.cn/{代码}/
示例：https://stockpage.10jqka.com.cn/600519/
```
提取：当前价、涨跌幅、PE、PB、技术指标信号

### S5-B：技术指标

**搜索词**：
```
"{股票简称} {代码} 同花顺 MACD KDJ RSI 技术指标 {YYYY年M月D日}"
"{股票简称} {代码} 均线 MA5 MA10 MA20 MA60 技术分析"
```
提取：各均线值、RSI(14)、MACD(DIF/DEA/柱)、KDJ(K/D/J)、BOLL(上/中/下轨)

### S5-C：主力资金（同花顺版）

**搜索词**：
```
"{股票简称} {代码} 同花顺 主力资金 净流入 {YYYY年M月}"
```

---

## 数据源 S6 — 通用 Web 搜索【兜底优先级】

> 前五个数据源均失败时，使用搜索引擎兜底。

### S6-A：行情搜索

```
搜索词："{股票简称} {代码} 今日收盘 {YYYY年M月D日} 证券之星"
搜索词："{股票简称} {代码} 股价 {YYYY年M月D日} 东方财富"
```

### S6-B：财务搜索

```
搜索词："{股票简称} {代码} {YYYY年}三季报/年报 净利润 同比 营收"
搜索词："{股票简称} {代码} 最新业绩快报 {YYYY年}"
```

### S6-C：行业政策搜索

```
搜索词："{行业关键词} 政策 补贴 规划 {YYYY年}"
搜索词："{行业关键词} 景气度 供需格局 {YYYY年} 最新"
```

### S6-D：公司公告搜索

```
搜索词："{股票简称} 中标 合同 订单 {YYYY年}"
搜索词："{股票简称} 大股东 减持 增持 公告 {YYYY年}"
搜索词："{股票简称} 监管处罚 立案 证监局 {YYYY年}"
```

---

## 市场情绪数据（大盘背景）

不依赖单一标的，每次分析时一并采集：

```
东方财富大盘数据 fetch：
https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&ut=&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:13,m:1+t:2,m:1+t:23&fields=f2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf12%2Cf14&_=

搜索词（备用）：
"今日 上证 深证 创业板 成交额 涨跌家数 涨停家数 跌停家数"
"今日 北向资金 净流入 陆股通"
```

提取：
- 上证指数：点位、涨跌幅
- 深证成指：点位、涨跌幅
- 创业板指：点位、涨跌幅
- 沪深300：点位、涨跌幅
- 全市场涨跌家数（上涨N家/下跌N家）
- 涨停家数、跌停家数
- 北向资金净流入（亿元）

---

## 数据采集失败处理规范

| 情况 | 处理方式 |
|------|---------|
| 单个字段所有6层数据源均失败 | 在报告该字段位置注明：`⚠️ 【字段名】数据获取失败，已尝试所有数据源，请手动查询：[建议查询URL]` |
| 技术指标数据缺失 | 注明：`⚠️ 技术指标数据不可用，建议访问同花顺或东方财富查看` |
| 财务数据缺失 | 注明：`⚠️ 财务数据暂缺（可能为新股、ST股或接口限制），建议通过巨潮资讯查看年报` |
| 行情数据缺失 | 终止分析并提示：`❌ 无法获取 {代码} 的实时行情数据，请确认代码正确，或在交易时段重试` |
| 数据明显异常（如PE=-9999） | 标记为无效，使用备用数据源补充，如仍无效则注明 |
