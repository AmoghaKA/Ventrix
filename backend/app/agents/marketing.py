import re

from typing import Dict, List, Sequence, Tuple

from app.db.models import Startup

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

                "industry", "sector", "market size", "market overview",

                "market landscape", "ecosystem", "addressable market",

                " tam ", " sam ",

            ),

            risk_terms=(

                "market decline", "market contraction",

                "regulatory pressure",

            ),

            critical_terms=("market collapse",),

            preferred_categories=("marketing", "company"),

        ),

        DimensionSpec(

            name="Market trends",

            keywords=(

                "trend", "demand", "adoption", "forecast", "cagr",

                "emerging", "growth", "tailwind", "headwind",

                "market shift", "industry trend", "consumer behaviour",

                "customer behaviour", "technology adoption",

                "digital transformation", "market opportunity",

                "changing preferences", "demand forecast",

                "industry growth", "market expansion", "future outlook",

            ),

            risk_terms=(

                "slowdown", "decline", "headwind", "saturation",

                "shrinking market",

            ),

            preferred_categories=("marketing",),

        ),

        DimensionSpec(

            name="Target customers",

            keywords=(

                "customer", "customers", "client", "clients",

                "target market", "smb", "enterprise", "mid-market",

                "mid-sized", "buyer", "user segment", "target audience",

                "customer segment", "customer profile", "ideal customer",

                "end user", "business customer", "consumer segment",

                "buyer persona", "customer demographics",

                "customer needs", "user demographics", "b2b", "b2c",

            ),

            risk_terms=(

                "customer concentration", "customer churn",

                "declining demand",

            ),

            preferred_categories=("marketing",),

        ),

        DimensionSpec(

            name="Competitor analysis",

            keywords=(

                "competitor", "competition", "competitive", "rival",

                "alternative", "market share", "incumbent",

                "direct competitor", "indirect competitor",

                "market leader", "market player", "substitute",

                "versus", "pricing", "pricing model",

                "product comparison", "competitor analysis",

                "competitive landscape",

            ),

            risk_terms=(

                "intense competition", "price war",

                "loss of market share", "dominant competitor",

                "high competition", "competitive pressure",

                "pricing pressure", "aggressive pricing",

                "low-cost competitor", "market saturation",

                "strong incumbent",

            ),

            preferred_categories=("marketing",),

        ),

        DimensionSpec(

            name="Market positioning",

            keywords=(

                "positioning", "positioned", "positions",

                "value proposition", "niche", "category leader",

                "brand", "differentiated",

            ),

            risk_terms=(

                "undifferentiated", "commoditized", "weak positioning",

            ),

            preferred_categories=("marketing", "company"),

        ),

        DimensionSpec(

            name="Competitive differentiation",

            keywords=(

                "differentiation", "proprietary", "unique", "moat",

                "competitive advantage", "integration", "workflow",

                "replicable",

            ),

            risk_terms=(

                "no moat", "easily replicated",

                "not differentiated", "commodity product",

            ),

            preferred_categories=("marketing", "company"),

        ),

        DimensionSpec(

            name="Growth opportunities",

            keywords=(

                "expansion", "opportunity", "new market",

                "partnership", "channel", "international", "upsell",

                "acquisition", "growth opportunity", "market penetration",

                "new customer segment", "product expansion",

                "strategic partnership", "distribution channel",

                "geographic expansion", "cross-selling", "scaling",

            ),

            risk_terms=(

                "limited growth", "stagnant", "declining demand",

            ),

            preferred_categories=("marketing",),

        ),

        DimensionSpec(

            name="Market risks",

            keywords=(

                "market risk", "threat", "regulatory", "dependence",

                "concentration", "churn", "pricing pressure",

                "saturation", "competition", "market uncertainty",

                "economic downturn", "changing regulations",

                "customer retention", "market volatility",

            ),

            risk_terms=(

                "market risk", "regulatory", "customer concentration",

                "churn", "pricing pressure", "saturation",

                "intense competition",

            ),

            critical_terms=(

                "market collapse", "loss of all customers",

            ),

            preferred_categories=("marketing",),

        ),

    )

    async def run(self, startup_id, context=None):
        """Run market analysis and attach evidence-backed competitor classifications."""
        output = await super().run(startup_id, context)

        try:
            if self.db is None or not startup_id:
                return output

            startup = (
                self.db.query(Startup)
                .filter(Startup.id == startup_id)
                .first()
            )
            if startup is None:
                return output

            analysis_id = self._analysis_id(context)
            evidence = self._load_evidence(startup_id, analysis_id, context)
            competitors = self._extract_competitors(evidence)

            classifications = [
                self._classify_competitor(competitor, evidence, startup)
                for competitor in competitors
            ]

            if output.detailed_explanations is None:
                output.detailed_explanations = {}

            if classifications:
                lines = []
                for item in classifications:
                    lines.append(
                        f"{item['name']}: {item['classification']} — "
                        f"{item['reason']} "
                        f"(Evidence ID: {item.get('evidence_id')})"
                    )
                output.detailed_explanations["Competitor classification"] = (
                    "\n".join(lines)
                )
            else:
                output.detailed_explanations["Competitor classification"] = (
                    "No explicitly named competitors were identified in the "
                    "retrieved market evidence."
                )

        except Exception as exc:
            self.logger.warning(
                "Competitor classification could not be added: %s",
                exc,
            )

        return output

    def _classify_competitor(
        self,
        competitor: Dict,
        evidence: Sequence,
        startup,
    ) -> Dict:
        """
        Classify a named competitor only when retrieved evidence explicitly
        supports the relationship. Otherwise return Unknown.
        """
        competitor_name = str(competitor.get("name", "")).strip()
        evidence_id = competitor.get("evidence_id")

        source = next(
            (
                item for item in evidence
                if self._evidence_value(item, "id") == evidence_id
            ),
            None,
        )

        source_text = self._evidence_text(source) if source is not None else ""
        lowered = source_text.casefold()
        startup_description = str(
            self._evidence_value(startup, "description", "") or ""
        ).strip()

        direct_patterns = (
            r"\bdirect competitor\b",
            r"\bdirect competition\b",
            r"\bsame product\b",
            r"\bsame service\b",
            r"\bsame solution\b",
        )
        indirect_patterns = (
            r"\bindirect competitor\b",
            r"\bindirect competition\b",
            r"\bsubstitute solution\b",
            r"\balternative approach\b",
            r"\bdifferent approach\b",
        )
        same_problem_patterns = (
            r"\bsame problem\b",
            r"\bsame need\b",
            r"\bsame customer problem\b",
            r"\bsolves the problem\b",
        )

        has_direct_signal = any(
            re.search(pattern, lowered) for pattern in direct_patterns
        )
        has_indirect_signal = any(
            re.search(pattern, lowered) for pattern in indirect_patterns
        )
        has_same_problem_signal = any(
            re.search(pattern, lowered) for pattern in same_problem_patterns
        )

        if has_direct_signal and startup_description:
            classification = "Direct"
            reason = (
                "The retrieved source explicitly describes a direct or "
                "same-solution competitor, and the startup has a description."
            )
        elif has_indirect_signal and has_same_problem_signal:
            classification = "Indirect"
            reason = (
                "The retrieved source describes a different or substitute "
                "approach addressing the same stated problem or need."
            )
        else:
            classification = "Unknown"
            if not startup_description:
                reason = (
                    "The startup description is missing, so product and "
                    "customer similarity cannot be assessed."
                )
            elif not source_text:
                reason = "The supporting source text is unavailable."
            else:
                reason = (
                    "The retrieved evidence names the competitor but does "
                    "not establish enough product, customer, or problem "
                    "similarity to classify it safely."
                )

        return {
            **competitor,
            "classification": classification,
            "reason": reason,
        }

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

            if category in spec.preferred_categories:

                score += 2

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

        matches.sort(

            key=lambda match: (

                match.score,

                self._evidence_value(match.evidence, "id"),

            ),

            reverse=True,

        )

        return matches[:5]

    def _extract_competitors(

        self,

        evidence: Sequence,

    ) -> List[Dict]:

        """

        Extract explicitly named competitors from retrieved evidence.

        Only extracts names following clear competitor-related phrases.

        Each result retains its source evidence for traceability.

        """

        patterns = (

            r"\bcompetitors?\s+include\s+(.+?)(?=\s+(?:in|across|within|for|while)\b|[.;:\n]|$)",

            r"\bcompetitors?\s+such\s+as\s+(.+?)(?=\s+(?:in|across|within|for|while)\b|[.;:\n]|$)",

            r"\bcompetes?\s+with\s+(.+?)(?=\s+(?:in|across|within|for|while)\b|[.;:\n]|$)",

            r"\brivals?\s+include\s+(.+?)(?=\s+(?:in|across|within|for|while)\b|[.;:\n]|$)",

            r"\brivals?\s+such\s+as\s+(.+?)(?=\s+(?:in|across|within|for|while)\b|[.;:\n]|$)",

            r"\balternatives?\s+include\s+(.+?)(?=\s+(?:in|across|within|for|while)\b|[.;:\n]|$)",

            r"\balternatives?\s+such\s+as\s+(.+?)(?=\s+(?:in|across|within|for|while)\b|[.;:\n]|$)",

        )

        generic_names = {

            "incumbents",

            "larger incumbents",

            "competitors",

            "other companies",

            "other providers",

            "market leaders",

            "established players",

            "other players",

            "leading companies",

            "major players",

        }

        competitors: Dict[str, Dict] = {}

        for item in evidence:

            text = self._evidence_text(item)

            for pattern in patterns:

                for match in re.finditer(

                    pattern, text, re.IGNORECASE

                ):

                    names_text = match.group(1)

                    names = re.split(

                        r",|\band\b|\b&\b|\bversus\b|\bvs\.?\b",

                        names_text,

                        flags=re.IGNORECASE,

                    )

                    for name in names:

                        name = name.strip(" \t\n:()-")

                        name = re.sub(

                            r"^(?:such as|including)\s+",

                            "",

                            name,

                            flags=re.IGNORECASE,

                        )

                        name = re.sub(

                            r"\s+(?:and other competitors|among others)$",

                            "",

                            name,

                            flags=re.IGNORECASE,

                        ).strip()

                        if not name:

                            continue

                        if name.casefold() in generic_names:

                            continue

                        if len(name.split()) > 5:

                            continue

                        # Avoid treating generic descriptions as company names.

                        if re.fullmatch(

                            r"(?:larger|smaller|leading|major|established|"

                            r"global|regional)\s+"

                            r"(?:incumbents|companies|players|providers)",

                            name,

                            re.IGNORECASE,

                        ):

                            continue

                        competitor_key = name.casefold()

                        if competitor_key not in competitors:

                            competitors[competitor_key] = {

                                "name": name,

                                "evidence_id": self._evidence_value(

                                    item, "id"

                                ),

                                "source_title": self._evidence_value(

                                    item, "source_title"

                                ),

                                "source_url": self._evidence_value(

                                    item, "source_url"

                                ),

                            }

        return list(competitors.values())
