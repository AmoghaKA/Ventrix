
import re
from typing import List, Sequence, Tuple

from app.agents.evidence_agent import (
    DimensionSpec,
    EvidenceAgent,
    _Match,
)


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
                "industry trend",
                "consumer behaviour",
                "customer behaviour",
                "technology adoption",
                "digital transformation",
                "market opportunity",
                "changing preferences",
                "demand forecast",
                "industry growth",
                "market expansion",
                "future outlook",
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
                "target audience",
                "customer segment",
                "customer profile",
                "ideal customer",
                "end user",
                "business customer",
                "consumer segment",
                "buyer persona",
                "customer demographics",
                "customer needs",
                "user demographics",
                "b2b",
                "b2c",
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
                "direct competitor",
                "indirect competitor",
                "market leader",
                "market player",
                "substitute",
                "versus",
                "pricing",
                "pricing model",
                "product comparison",
                "competitor analysis",
                "competitive landscape",
            ),
            risk_terms=(
                "intense competition",
                "price war",
                "loss of market share",
                "dominant competitor",
                "high competition",
                "competitive pressure",
                "pricing pressure",
                "aggressive pricing",
                "low-cost competitor",
                "market saturation",
                "strong incumbent",
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
                "market penetration",
                "new customer segment",
                "product expansion",
                "strategic partnership",
                "distribution channel",
                "geographic expansion",
                "cross-selling",
                "scaling",
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
                "market uncertainty",
                "economic downturn",
                "changing regulations",
                "customer retention",
                "market volatility",
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
            critical_terms=(
                "market collapse",
                "loss of all customers",
            ),
            preferred_categories=("marketing",),
        ),
    )

    def _match_dimension(
        self,
        spec: DimensionSpec,
        evidence: Sequence,
    ) -> List[_Match]:
        """Match relevant evidence using complete words and phrases."""

        matches: List[_Match] = []

        for item in evidence:
            text = self._evidence_text(item)
            lowered = text.lower()

            hits = [
                keyword
                for keyword in spec.keywords
                if re.search(
                    r"(?<!\w)" + re.escape(keyword.strip()) + r"(?!\w)",
                    lowered,
                )
            ]

            if not hits:
                continue

            category = str(
                self._evidence_value(item, "source_category") or ""
            ).lower()

            title = str(
                self._evidence_value(item, "source_title") or ""
            )

            score = len(hits)

            # Prefer evidence from relevant source categories.
            if category in spec.preferred_categories:
                score += 2

            # Give additional weight when the title contains a matched keyword.
            if any(
                re.search(
                    r"(?<!\w)" + re.escape(keyword.strip()) + r"(?!\w)",
                    title.lower(),
                )
                for keyword in hits
            ):
                score += 1

            matches.append(
                _Match(
                    evidence=item,
                    text=text,
                    snippet=self._best_snippet(text, hits),
                    score=score,
                )
            )

        # Rank evidence by relevance score, then evidence ID.
        matches.sort(
            key=lambda match: (
                match.score,
                self._evidence_value(match.evidence, "id"),
            ),
            reverse=True,
        )

        # Return only the five most relevant evidence sources.
        return matches[:5]
