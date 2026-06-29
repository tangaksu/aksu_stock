"""M01 公司基础与业务拆解"""
from __future__ import annotations
from .base import ModuleResult, score_to_stars


def analyze_business(data: dict) -> ModuleResult:
    info = data.get("stock_info") or {}
    rt = data.get("realtime") or {}

    findings = []
    score = 5.0  # 基础分

    name = info.get("name") or rt.get("name", data.get("code", ""))
    industry = info.get("industry", "")
    board = info.get("board", "")
    list_date = info.get("list_date", "")
    business = info.get("business", "")
    market_cap = info.get("market_cap", "")
    float_cap = info.get("float_cap", "")
    pe_ttm = info.get("pe_ttm", "")
    pb = info.get("pb", "")

    if name:
        findings.append(f"公司全称：{name}，股票代码：{data.get('code', '')}")
    if industry:
        findings.append(f"所属行业：{industry}，上市板块：{board}")
    if list_date:
        findings.append(f"上市时间：{list_date}")
    if business:
        findings.append(f"主营业务：{business[:100]}{'...' if len(business) > 100 else ''}")
    if market_cap:
        findings.append(f"总市值：{market_cap}，流通市值：{float_cap}")
    if pe_ttm:
        findings.append(f"市盈率(动)：{pe_ttm}，市净率：{pb}")

    # 评分调整：有主营业务描述 +1，有行业信息 +1
    if business:
        score += 1.0
    if industry:
        score += 1.0
    if market_cap:
        # 大市值（超100亿）稳定性更高
        try:
            cap_val = float(str(market_cap).replace("亿", "").replace(",", ""))
            if cap_val > 500:
                score += 2.0
                findings.append("✅ 大市值蓝筹，流动性充裕，机构重仓偏好")
            elif cap_val > 100:
                score += 1.0
                findings.append("✅ 中市值标的，兼具弹性与稳定性")
            else:
                findings.append("⚠️ 小市值标的，波动风险较大")
        except Exception:
            pass

    score = min(10.0, max(1.0, score))

    # 判断企业类型
    company_type = "普通型"
    if industry:
        if any(k in industry for k in ["白酒", "消费", "医药", "食品"]):
            company_type = "防御型"
        elif any(k in industry for k in ["科技", "芯片", "AI", "新能源", "生物"]):
            company_type = "成长型"
        elif any(k in industry for k in ["钢铁", "煤炭", "化工", "有色", "地产"]):
            company_type = "周期型"

    conclusion = (
        f"{name} 属于 {industry} 行业 {company_type}标的，"
        f"上市于 {board} 板块，建议结合基本面与周期位置匹配对应投资策略。"
    )

    return ModuleResult(
        module_id="M01",
        module_name="公司基础与业务拆解",
        score=round(score, 1),
        stars=score_to_stars(score),
        key_findings=findings,
        short_advice="关注近期公告与主营业务变化，判断短期催化",
        mid_advice=f"重点跟踪 {industry} 行业景气度与公司市场份额变化",
        long_advice=f"评估 {company_type} 属性对应的估值体系与长期持有价值",
        conclusion=conclusion,
        detail=info,
    )
