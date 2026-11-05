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
        Classify a named competitor using explicit, source-backed signals.

        Direct:
            The source explicitly describes the company as a direct competitor
            (or clearly says it competes directly), and the source supports
            overlap in both product/solution and customer segments.

        Indirect:
            The source explicitly describes a different/substitute approach
            that addresses the same customer problem or need.

        Unknown:
            The available evidence does not establish either relationship.
        """
        competitor_name = str(competitor.get("name", "")).strip()
        evidence_id = competitor.get("evidence_id")

        source = next(
            (
                item
                for item in evidence
                if self._evidence_value(item, "id") == evidence_id
            ),
            None,
        )

        source_text = self._evidence_text(source) if source is not None else ""

        startup_description = str(
            self._evidence_value(startup, "description", "") or ""
        )

        startup_industry = str(
            self._evidence_value(startup, "industry", "") or ""
        )

        startup_profile = (
            f"{startup_description} {startup_industry}"
        ).casefold()

        if not competitor_name:
            return {
                **competitor,
                "classification": "Unknown",
                "reason": (
                    "The competitor name is missing from the extracted evidence."
                ),
            }

        # Confirm that the named company actually appears in its cited source.
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", source_text)
            if sentence.strip()
        ]

        competitor_sentences = [
            sentence
            for sentence in sentences
            if re.search(
                r"(?<!\w)" + re.escape(competitor_name) + r"(?!\w)",
                sentence,
                re.IGNORECASE,
            )
        ]

        competitor_is_in_source = bool(competitor_sentences)

        competitor_context = " ".join(
            competitor_sentences
        ).casefold()

        if not source_text:
            classification = "Unknown"
            reason = "The supporting source text is unavailable."

        elif not competitor_is_in_source:
            classification = "Unknown"
            reason = (
                "The cited source does not contain the extracted competitor name, "
                "so its relationship cannot be verified."
            )

        else:
            # These signals must be explicitly present in the source text.
            direct_signal = any(
                re.search(pattern, competitor_context)
                for pattern in (
                    r"\bdirect competitor\b",
                    r"\bdirect competition\b",
                    r"\bcompetes? directly\b",
                    r"\bcompeting directly\b",
                    r"\bcompete head[- ]to[- ]head\b",
                    r"\bsame product category\b",
                    r"\bsimilar product\b",
                    r"\bsimilar service\b",
                    r"\bsimilar solution\b",
                    r"\bsame product\b",
                    r"\bsame service\b",
                    r"\bsame solution\b",
                )
            )

            # Remove common words so generic overlap cannot establish a match.
            stop_words = {
                "about", "across", "also", "and", "are", "as", "based", "being",
                "business", "businesses", "company", "companies", "customer",
                "customers", "for", "from", "has", "have", "into", "its", "more",
                "offers", "provides", "serves", "solution", "solutions", "that",
                "their", "them", "these", "this", "those", "through", "to", "use",
                "using", "with", "within", "the", "they", "which", "will",
                "would", "can", "could", "but", "not",
            }

            def meaningful_terms(value: str) -> set:
                return {
                    token
                    for token in re.findall(r"[a-z0-9]+", value.casefold())
                    if len(token) > 2 and token not in stop_words
                }

            # Compare the startup's description and industry with the cited source.
            startup_terms = meaningful_terms(startup_profile)
            source_terms = meaningful_terms(competitor_context)
            shared_terms = startup_terms & source_terms

            product_terms = {
                "software", "automation", "workflow", "analytics", "crm",
                "payments", "accounting", "marketplace", "security", "cloud",
                "database", "recruitment", "logistics", "fintech", "saas",
                "platform", "application", "app", "tool", "service",
                "healthcare", "education", "ecommerce", "commerce", "banking",
                "insurance", "manufacturing", "communication", "marketing",
                "sales", "human", "resources", "cybersecurity",
            }

            customer_terms = {
                "enterprise", "smb", "startup", "startups", "mid", "market",
                "finance", "financial", "teams", "team", "retail", "healthcare",
                "consumers", "developers", "manufacturers", "schools", "banks",
                "individuals", "students", "patients", "doctors", "employees",
                "recruiters", "merchants", "small", "medium", "large",
                "organizations", "professionals",
            }

            product_overlap = shared_terms & product_terms
            customer_overlap = shared_terms & customer_terms

            if direct_signal and product_overlap and customer_overlap:
                classification = "Direct"
                reason = (
                    "The cited source explicitly indicates direct competition, "
                    "and it supports overlap with the startup in both product/"
                    "industry and target-customer terms."
                )

            else:
                indirect_signal = any(
                    re.search(pattern, competitor_context)
                    for pattern in (
                        r"\bindirect competitor\b",
                        r"\bindirect competition\b",
                        r"\bsubstitute solution\b",
                        r"\balternative approach\b",
                        r"\bdifferent approach\b",
                        r"\bdifferent product\b",
                        r"\bother way to\b",
                        r"\bsubstitute for\b",
                        r"\balternative to\b",
                    )
                )

                same_problem_signal = any(
                    re.search(pattern, competitor_context)
                    for pattern in (
                        r"\bsame problem\b",
                        r"\bsame need\b",
                        r"\bsame customer problem\b",
                        r"\bsolves? the same problem\b",
                        r"\bsolves? the problem\b",
                        r"\baddresses? the same need\b",
                        r"\bserves? the same need\b",
                        r"\baddresses? the same problem\b",
                    )
                )

                if indirect_signal and same_problem_signal:
                    classification = "Indirect"
                    reason = (
                        "The cited source connects this named company to a "
                        "different or substitute approach that addresses the "
                        "same customer problem or need."
                    )

                else:
                    classification = "Unknown"

                    if not startup_profile.strip():
                        reason = (
                            "The startup description and industry are missing, "
                            "so product and customer overlap cannot be assessed."
                        )

                    elif not direct_signal and not indirect_signal:
                        reason = (
                            "The cited source names the company but does not "
                            "explicitly establish whether it is a direct or "
                            "indirect competitor."
                        )

                    elif direct_signal:
                        reason = (
                            "The source indicates direct competition, but it "
                            "does not establish both product/industry overlap "
                            "and target-customer overlap."
                        )

                    else:
                        reason = (
                            "The source suggests an alternative approach but "
                            "does not clearly establish that it addresses the "
                            "same customer problem or need."
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