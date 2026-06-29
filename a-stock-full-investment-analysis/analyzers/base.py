"""
通用分析工具函数与模块结果数据类
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


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
        return "N/A"
    return f"{v:+.2f}{suffix}" if v != 0 else f"0.00{suffix}"


def fmt(v: float | None, decimals: int = 2, suffix: str = "") -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}{suffix}"


def yi(v: float | None) -> str:
    """元转亿元显示"""
    if v is None:
        return "N/A"
    return f"{v / 1e8:.2f}亿"
