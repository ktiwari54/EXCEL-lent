"""
Data Analyst Engine — processing architecture.

AI/Intent → Semantic → BI → (Formula|Lookup|Time|Stats|KPI) → Insight → Result
"""

from app.engines.bi_engine import BusinessIntelligenceEngine

__all__ = ["BusinessIntelligenceEngine"]
