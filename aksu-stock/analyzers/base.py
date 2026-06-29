"""
analyzers/base.py — 所有分析模块的基础数据结构。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleResult:
    """
    单个分析模块的标准化输出结构。
    score: 1.0 - 10.0 分（模块内评分）
    stars: 1 - 5 星
    key_findings: 关键发现列表（至少3条）
    short_advice:  短线建议（1-7交易日）
    mid_advice:    中线建议（1-3个月）
    long_advice:   长线建议（6-12个月）
    conclusion:    模块核心结论（一句话）
    detail:        扩展字段，供 M16/M17 汇总或 HTML 渲染使用
    """
    module_id: str
    module_name: str
    score: float       # 1.0-10.0
    stars: int         # 1-5
    key_findings: list[str]
    short_advice: str = ""
    mid_advice: str = ""
    long_advice: str = ""
    conclusion: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.score = max(1.0, min(10.0, float(self.score)))
        self.stars = max(1, min(5, int(self.stars)))

    @property
    def score_label(self) -> str:
        if self.score >= 9:
            return "极优"
        if self.score >= 7:
            return "良好"
        if self.score >= 5:
            return "中性"
        if self.score >= 3:
            return "偏弱"
        return "极差"

    @property
    def stars_str(self) -> str:
        return "★" * self.stars + "☆" * (5 - self.stars)


def score_to_stars(score: float) -> int:
    """将 1-10 分映射到 1-5 星"""
    if score >= 9:
        return 5
    if score >= 7:
        return 4
    if score >= 5:
        return 3
    if score >= 3:
        return 2
    return 1


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """安全嵌套取值，任意层级不存在时返回 default。"""
    cur = data
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
        if cur is None:
            return default
    return cur


def safe_float(v: Any, default: float | None = None) -> float | None:
    """安全转 float，异常或 NaN/Inf 返回 default。"""
    try:
        if v in (None, "", "—", "N/A", "-"):
            return default
        result = float(v)
        import math
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def pct_str(v: float | None, suffix: str = "%") -> str:
    """将 float 格式化为百分比字符串，None 时返回 '—'"""
    if v is None:
        return "—"
    return f"{v:.2f}{suffix}"


def fmt_number(v: float | None, decimal: int = 2, unit: str = "") -> str:
    """格式化数字，None 时返回 '—'"""
    if v is None:
        return "—"
    return f"{v:.{decimal}f}{unit}"
