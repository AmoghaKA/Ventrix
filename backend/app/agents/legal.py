from typing import Tuple

from app.agents.evidence_agent import DimensionSpec, EvidenceAgent


class LegalAgent(EvidenceAgent):
    """Evidence-backed legal and compliance due diligence agent.

    The agent never states that a company is legally compliant merely because a
    public page describes compliance. It reports only what the evidence shows
    and records missing legal documentation explicitly.
    """

    AGENT_NAME = "Legal Agent"
    MISSING_LABEL = "Missing legal documentation"
    RELEVANT_CATEGORIES = ("legal", "company")
    CAVEAT = (
        "A public statement describing compliance is not independent proof of "
        "legal compliance. No legal conclusion has been inferred beyond the "
        "retrieved evidence."
    )
    DIMENSION_SPECS: Tuple[DimensionSpec, ...] = (
        DimensionSpec(
            name="Company registration information",
            keywords=(
                "registered",
                "registration",
                "company number",
                "incorporation",
                "incorporated",
                "jurisdiction",
                "registered office",
                "legal entity",
                "articles of association",
                "good standing",
                "vat number",
                "tax id",
            ),
            risk_terms=(
                "struck off",
                "dissolved",
                "not registered",
                "registration revoked",
            ),
            critical_terms=("fraud", "criminal"),
            preferred_categories=("legal",),
        ),
        DimensionSpec(
            name="Public regulatory disclosures",
            keywords=(
                "regulator",
                "regulatory",
                "filing",
                "disclosure",
                "annual report",
                "license",
                "licensed",
                "permit",
                "authority",
                "securities commission",
                "data protection authority",
            ),
            risk_terms=(
                "investigation",
                "enforcement",
                "warning",
                "breach",
                "penalty",
                "regulatory action",
            ),
            critical_terms=("criminal", "fraud", "sanction", "injunction"),
            preferred_categories=("legal",),
        ),
        DimensionSpec(
            name="Available legal records",
            keywords=(
                "litigation",
                "lawsuit",
                "court",
                "legal proceeding",
                "dispute",
                "judgment",
                "arbitration",
                "claim",
                "complaint",
                "settlement",
                "injunction",
            ),
            risk_terms=(
                "litigation",
                "lawsuit",
                "court",
                "claim",
                "dispute",
                "judgment",
                "settlement",
            ),
            critical_terms=("injunction", "criminal", "fraud"),
            preferred_categories=("legal",),
        ),
        DimensionSpec(
            name="Compliance concerns",
            keywords=(
                "compliance",
                "gdpr",
                "privacy",
                "data protection",
                "anti-bribery",
                "anti bribery",
                "aml",
                "kyc",
                "sanctions",
                "policy",
                "certification",
                "iso 27001",
                "soc 2",
                "audit",
            ),
            risk_terms=(
                "non-compliance",
                "breach",
                "fine",
                "penalty",
                "investigation",
                "data breach",
                "sanction",
            ),
            critical_terms=("criminal", "fraud", "sanction", "injunction"),
            preferred_categories=("legal",),
        ),
        DimensionSpec(
            name="Potential intellectual property concerns",
            keywords=(
                "intellectual property",
                "trademark",
                "patent",
                "copyright",
                "trade secret",
                "licensing",
                "infringement",
                "ownership",
                "assignment",
            ),
            risk_terms=(
                "infringement",
                "opposition",
                "unlicensed",
                "ownership claim",
                "ip dispute",
            ),
            critical_terms=("injunction", "counterfeit"),
            preferred_categories=("legal",),
        ),
    )
