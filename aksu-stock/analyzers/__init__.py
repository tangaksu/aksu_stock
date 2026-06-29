"""
analyzers/__init__.py — 分析器包初始化，统一导出所有分析函数。
"""
from analyzers.base import ModuleResult

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
from analyzers.m16_timing import analyze_timing
from analyzers.m17_summary import analyze_summary

__all__ = [
    "ModuleResult",
    "analyze_business",
    "analyze_financial",
    "analyze_governance",
    "analyze_industry",
    "analyze_valuation",
    "analyze_technical",
    "analyze_capital",
    "analyze_sentiment",
    "analyze_consensus",
    "analyze_market",
    "analyze_liquidity",
    "analyze_catalyst",
    "analyze_history",
    "analyze_risk_control",
    "analyze_peer",
    "analyze_timing",
    "analyze_summary",
]
