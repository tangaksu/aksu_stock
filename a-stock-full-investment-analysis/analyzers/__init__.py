"""16大分析模块，每个模块返回标准化分析结果"""
from .m01_business import analyze_business
from .m02_financial import analyze_financial
from .m03_governance import analyze_governance
from .m04_industry import analyze_industry
from .m05_valuation import analyze_valuation
from .m06_technical import analyze_technical
from .m07_capital import analyze_capital
from .m08_sentiment import analyze_sentiment
from .m09_consensus import analyze_consensus
from .m10_market import analyze_market
from .m11_liquidity import analyze_liquidity
from .m12_catalyst import analyze_catalyst
from .m13_history import analyze_history
from .m14_risk_control import analyze_risk_control
from .m15_peer import analyze_peer
from .m16_summary import analyze_summary

__all__ = [
    "analyze_business", "analyze_financial", "analyze_governance",
    "analyze_industry", "analyze_valuation", "analyze_technical",
    "analyze_capital", "analyze_sentiment", "analyze_consensus",
    "analyze_market", "analyze_liquidity", "analyze_catalyst",
    "analyze_history", "analyze_risk_control", "analyze_peer",
    "analyze_summary",
]
