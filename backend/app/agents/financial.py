from typing import Tuple

from app.agents.evidence_agent import DimensionSpec, EvidenceAgent


class FinancialAgent(EvidenceAgent):
    """Evidence-backed financial due diligence agent.

    The agent does not estimate revenue, profitability, cash flow, liquidity,
    or liabilities when those figures are absent. Unavailable fields are
    reported as missing information.
    """

    AGENT_NAME = "Financial Agent"
    MISSING_LABEL = "Missing financial information"
    RELEVANT_CATEGORIES = ("financial", "company")
    CAVEAT = (
        "Public statements are not audited financial statements, and no "
        "financial figure has been estimated or inferred."
    )
    DIMENSION_SPECS: Tuple[DimensionSpec, ...] = (
        DimensionSpec(
            name="Funding history",
            keywords=(
                "funding",
                "funded",
                "raised",
                "raise",
                "seed",
                "pre-seed",
                "series a",
                "series b",
                "series c",
                "round",
                "investor",
                "backer",
                "venture",
                "grant",
                "capital",
            ),
            risk_terms=(
                "failed to raise",
                "funding shortfall",
                "down round",
                "bridge financing",
            ),
            critical_terms=("insolvency", "insolvent"),
            preferred_categories=("financial",),
        ),
        DimensionSpec(
            name="Revenue",
            keywords=(
                "revenue",
                "arr",
                "mrr",
                "sales",
                "turnover",
                "top line",
                "bookings",
                "subscription revenue",
                "recurring revenue",
            ),
            risk_terms=(
                "revenue decline",
                "declining revenue",
                "no revenue",
                "revenue shortfall",
                "sales decline",
            ),
            preferred_categories=("financial",),
        ),
        DimensionSpec(
            name="Profitability",
            keywords=(
                "profit",
                "profitable",
                "profitability",
                "margin",
                "ebitda",
                "net income",
                "net loss",
                "loss-making",
                "unprofitable",
                "earnings",
            ),
            risk_terms=(
                "net loss",
                "loss-making",
                "unprofitable",
                "negative margin",
                "declining margin",
                "operating loss",
            ),
            critical_terms=("insolvency", "insolvent", "going concern"),
            preferred_categories=("financial",),
        ),
        DimensionSpec(
            name="Cash flow",
            keywords=(
                "cash flow",
                "operating cash",
                "free cash flow",
                "cash generation",
                "burn",
                "cash burn",
                "runway",
                "monthly burn",
            ),
            risk_terms=(
                "negative cash flow",
                "cash burn",
                "burn rate",
                "short runway",
                "cash shortfall",
            ),
            critical_terms=("going concern", "insolvency", "insolvent"),
            preferred_categories=("financial",),
        ),
        DimensionSpec(
            name="Liquidity",
            keywords=(
                "liquidity",
                "cash balance",
                "cash reserves",
                "available cash",
                "current ratio",
                "working capital",
                "bank balance",
            ),
            risk_terms=(
                "liquidity risk",
                "insufficient liquidity",
                "low cash",
                "current ratio below",
                "working capital deficit",
            ),
            critical_terms=(
                "cannot meet obligations",
                "insolvency",
                "insolvent",
            ),
            preferred_categories=("financial",),
        ),
        DimensionSpec(
            name="Debt and liabilities",
            keywords=(
                "debt",
                "loan",
                "liability",
                "liabilities",
                "credit facility",
                "convertible note",
                "borrowings",
                "obligation",
                "secured",
                "outstanding",
            ),
            risk_terms=(
                "high debt",
                "significant liabilities",
                "overdue",
                "covenant breach",
                "debt default",
                "credit risk",
            ),
            critical_terms=("default", "insolvency", "insolvent", "bankruptcy"),
            preferred_categories=("financial",),
        ),
        DimensionSpec(
            name="Financial strengths",
            keywords=(
                "is profitable",
                "remained profitable",
                "profitable business",
                "positive cash flow",
                "debt-free",
                "debt free",
                "strong margin",
                "recurring revenue growth",
                "capital efficient",
                "revenue growth",
                "financial strength",
            ),
            preferred_categories=("financial",),
        ),
        DimensionSpec(
            name="Financial risks",
            keywords=(
                "financial risk",
                "risk",
                "exposure",
                "volatility",
                "currency",
                "downturn",
                "credit",
                "loss",
                "burn",
                "liquidity",
                "going concern",
                "concentration",
            ),
            risk_terms=(
                "financial risk",
                "loss",
                "cash burn",
                "liquidity",
                "going concern",
                "high debt",
                "overdue",
                "default",
                "currency exposure",
            ),
            critical_terms=(
                "insolvency",
                "insolvent",
                "bankruptcy",
                "going concern",
                "fraud",
            ),
            preferred_categories=("financial",),
        ),
    )
