"""通用分析工具函数与模块结果数据类"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

DATA_MISSING_TEXT = "⚠️ 数据获取失败（字段缺失或上游接口未返回）"


@dataclass
class ModuleResult:
    """标准化模块分析结果"""
    module_id: str          # M01 ~ M16
    module_name: str
    score: float            # 1-10
    stars: int              # 1-5
    key_findings: list[str] = field(default_factory=list)
    short_advice: str = ""  # 短线建议
    mid_advice: str = ""    # 中线建议
    long_advice: str = ""   # 长线建议
    conclusion: str = ""    # 核心结论
    detail: dict = field(default_factory=dict)  # 原始详细数据

    @property
    def star_str(self) -> str:
        return "★" * self.stars + "☆" * (5 - self.stars)

    @property
    def score_color(self) -> str:
        if self.score >= 8:
            return "#16a34a"
        if self.score >= 6:
            return "#ca8a04"
        return "#dc2626"


def score_to_stars(score: float) -> int:
    """10分制转5星"""
    if score >= 9:
        return 5
    if score >= 7:
        return 4
    if score >= 5:
        return 3
    if score >= 3:
        return 2
    return 1


def pct_fmt(v: float | None, suffix: str = "%") -> str:
    if v is None:
        return DATA_MISSING_TEXT
    return f"{v:+.2f}{suffix}" if v != 0 else f"0.00{suffix}"


def fmt(v: float | None, decimals: int = 2, suffix: str = "") -> str:
    if v is None:
        return DATA_MISSING_TEXT
    return f"{v:.{decimals}f}{suffix}"


def yi(v: float | None) -> str:
    """元转亿元显示"""
    if v is None:
        return DATA_MISSING_TEXT
    return f"{v / 1e8:.2f}亿"


def calc_trade_levels(price: float | None, ma10: float | None = None, ma20: float | None = None) -> dict[str, float | None]:
    """统一计算入场/止损/止盈参数。"""
    if price is None:
        return {
            "entry_low": ma10,
            "entry_high": None,
            "stop_loss": ma20,
            "take_profit_1": None,
            "take_profit_2": None,
            "take_profit_3": None,
        }
    fallback_entry = round(price * 0.98, 2)
    entry_low = round(ma10, 2) if ma10 is not None else fallback_entry
    entry_high = round(price * 1.02, 2)
    ma20_stop = round(ma20, 2) if ma20 is not None else None
    hard_stop = round(price * 0.92, 2)
    stop_loss = max(ma20_stop, hard_stop) if ma20_stop is not None else hard_stop
    return {
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop_loss": round(stop_loss, 2),
        "take_profit_1": round(price * 1.08, 2),
        "take_profit_2": round(price * 1.15, 2),
        "take_profit_3": round(price * 1.25, 2),
    }


def position_from_total_score(total_score: float | None) -> str:
    """统一综合评分对应仓位建议。"""
    if total_score is None:
        return "⚠️ 综合评分缺失，暂不建议建仓"
    if total_score >= 90:
        return "30-50%"
    if total_score >= 80:
        return "20-35%"
    if total_score >= 70:
        return "10-20%"
    if total_score >= 60:
        return "5-10%"
    return "0%"


def extract_risk_findings(module_results: dict[str, ModuleResult], limit: int | None = None) -> list[str]:
    """从模块结果中抽取风险信号。"""
    risks: list[str] = []
    for module_id in sorted(module_results.keys()):
        result = module_results[module_id]
        for finding in result.key_findings:
            if "🚨" in finding or "⚠️" in finding:
                risks.append(f"{module_id} {finding}")
    return risks[:limit] if limit else risks


def extract_positive_findings(module_results: dict[str, ModuleResult], limit: int | None = None) -> list[str]:
    """从模块结果中抽取正向亮点。"""
    positives: list[str] = []
    for module_id in sorted(module_results.keys()):
        result = module_results[module_id]
        for finding in result.key_findings:
            if "✅" in finding:
                positives.append(f"{module_id} {finding}")
    return positives[:limit] if limit else positives
