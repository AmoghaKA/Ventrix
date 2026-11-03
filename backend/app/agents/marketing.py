from typing import Tuple

from app.agents.evidence_agent import DimensionSpec, EvidenceAgent


class MarketingAgent(EvidenceAgent):
    """Evidence-backed market and marketing due diligence agent."""

    AGENT_NAME = "Marketing Agent"
    MISSING_LABEL = "Missing market information"
    RELEVANT_CATEGORIES = ("marketing", "company")
    CAVEAT = (
        "Market evidence is limited to retrieved public sources; marketing "
        "claims have not been independently validated."
    )
    DIMENSION_SPECS: Tuple[DimensionSpec, ...] = (
        DimensionSpec(
            name="Industry overview",
            keywords=(
                "industry",
                "sector",
                "market size",
                "market overview",
                "market landscape",
                "ecosystem",
                "addressable market",
                " tam ",
                " sam ",
            ),
            risk_terms=(
                "market decline",
                "market contraction",
                "regulatory pressure",
            ),
            critical_terms=("market collapse",),
            preferred_categories=("marketing", "company"),
        ),
        DimensionSpec(
            name="Market trends",
            keywords=(
                "trend",
                "demand",
                "adoption",
                "forecast",
                "cagr",
                "emerging",
                "growth",
                "tailwind",
                "headwind",
                "market shift",
            ),
            risk_terms=(
                "slowdown",
                "decline",
                "headwind",
                "saturation",
                "shrinking market",
            ),
            preferred_categories=("marketing",),
        ),
        DimensionSpec(
            name="Target customers",
            keywords=(
                "customer",
                "customers",
                "client",
                "clients",
                "target market",
                "smb",
                "enterprise",
                "mid-market",
                "mid-sized",
                "buyer",
                "user segment",
            ),
            risk_terms=(
                "customer concentration",
                "customer churn",
                "declining demand",
            ),
            preferred_categories=("marketing",),
        ),
        DimensionSpec(
            name="Competitor analysis",
            keywords=(
                "competitor",
                "competition",
                "competitive",
                "rival",
                "alternative",
                "market share",
                "incumbent",
            ),
            risk_terms=(
                "intense competition",
                "price war",
                "loss of market share",
                "dominant competitor",
            ),
            preferred_categories=("marketing",),
        ),
        DimensionSpec(
            name="Market positioning",
            keywords=(
                "positioning",
                "positioned",
                "positions",
                "value proposition",
                "niche",
                "category leader",
                "brand",
                "differentiated",
            ),
            risk_terms=(
                "undifferentiated",
                "commoditized",
                "weak positioning",
            ),
            preferred_categories=("marketing", "company"),
        ),
        DimensionSpec(
            name="Competitive differentiation",
            keywords=(
                "differentiation",
                "proprietary",
                "unique",
                "moat",
                "competitive advantage",
                "integration",
                "workflow",
                "replicable",
            ),
            risk_terms=(
                "no moat",
                "easily replicated",
                "not differentiated",
                "commodity product",
            ),
            preferred_categories=("marketing", "company"),
        ),
        DimensionSpec(
            name="Growth opportunities",
            keywords=(
                "expansion",
                "opportunity",
                "new market",
                "partnership",
                "channel",
                "international",
                "upsell",
                "acquisition",
                "growth opportunity",
            ),
            risk_terms=(
                "limited growth",
                "stagnant",
                "declining demand",
            ),
            preferred_categories=("marketing",),
        ),
        DimensionSpec(
            name="Market risks",
            keywords=(
                "market risk",
                "threat",
                "regulatory",
                "dependence",
                "concentration",
                "churn",
                "pricing pressure",
                "saturation",
                "competition",
            ),
            risk_terms=(
                "market risk",
                "regulatory",
                "customer concentration",
                "churn",
                "pricing pressure",
                "saturation",
                "intense competition",
            ),
            critical_terms=("market collapse", "loss of all customers"),
            preferred_categories=("marketing",),
        ),
    )
