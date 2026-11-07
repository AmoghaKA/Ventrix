from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.output import (
    AgentOutput,
    EvidenceReference,
    EvidenceStatus,
    ExecutionStatus,
    RiskLevel,
)
from app.db.models import Evidence

_RISK_ORDER = {
    RiskLevel.UNKNOWN: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}

_STATUS_ORDER = {
    EvidenceStatus.UNAVAILABLE: 0,
    EvidenceStatus.UNVERIFIED: 1,
    EvidenceStatus.PARTIALLY_VERIFIED: 2,
    EvidenceStatus.VERIFIED: 3,
}


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    CONFLICTING = "CONFLICTING"
    UNAVAILABLE = "UNAVAILABLE"


# Backwards-compatible alias for the earlier finding status name.
VerificationFindingStatus = VerificationStatus


class SourceReliabilityAssessment(BaseModel):
    evidence_id: int
    source_title: str
    source_url: str
    verification_status: EvidenceStatus
    reliability_score: float = Field(ge=0, le=1)
    reliability_level: str
    factors: List[str] = Field(default_factory=list)


class VerificationContradiction(BaseModel):
    agents: List[str] = Field(default_factory=list)
    dimension: Optional[str] = None
    claim_a: str
    claim_b: str
    evidence_ids: List[int] = Field(default_factory=list)
    severity: RiskLevel = RiskLevel.UNKNOWN
    reasoning: str


class VerificationClaimReview(BaseModel):
    agent_key: str
    agent_name: str
    dimension: str
    claim: str
    risk_level: RiskLevel
    claimed_evidence_status: EvidenceStatus
    verified_evidence_status: EvidenceStatus
    verification_status: VerificationStatus
    supporting_evidence_ids: List[int] = Field(default_factory=list)
    supporting_evidence: List[EvidenceReference] = Field(default_factory=list)
    reasoning: str


class VerificationOutput(BaseModel):
    agent_name: str = "Verification Agent"
    analysis_id: int
    execution_status: ExecutionStatus
    status: VerificationStatus
    verification_status: VerificationStatus
    total_findings: int = 0
    checked_references: int = 0
    valid_references: int = 0
    invalid_references: int = 0
    claims_reviewed: List[VerificationClaimReview] = Field(default_factory=list)
    supporting_evidence: List[EvidenceReference] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    contradictions: List[VerificationContradiction] = Field(default_factory=list)
    source_reliability: List[SourceReliabilityAssessment] = Field(
        default_factory=list
    )
    missing_evidence: List[str] = Field(default_factory=list)
    detailed_reasoning: str = ""
    investor_impact: str = ""
    results: List[VerificationClaimReview] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    specialist_statuses: Dict[str, str] = Field(default_factory=dict)
    error_details: Optional[str] = None


class VerificationAgent(BaseAgent):
    AGENT_NAME = "Verification Agent"

    def __init__(self, db: Optional[Session] = None) -> None:
        super().__init__(self.AGENT_NAME)
        self.db = db

    async def run(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> VerificationOutput:
        try:
            analysis_id = self._analysis_id(context)
            outputs = self._normalise_outputs((context or {}).get("specialist_outputs"))
            specialist_errors = (context or {}).get("specialist_errors") or {}
            evidence = self._load_evidence(analysis_id, startup_id)
            return self._build_output(
                analysis_id,
                outputs,
                specialist_errors,
                evidence,
            )
        except Exception as exc:
            self.logger.error(f"Agent {self.name} failed: {exc}")
            return self._error_output(context, exc)

    def structured_error_output(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> VerificationOutput:
        return self._error_output(context, error)

    def _analysis_id(self, context: Optional[Dict[str, Any]]) -> int:
        if not context or context.get("analysis_id") is None:
            raise ValueError("analysis_id is required in the agent context")
        try:
            analysis_id = int(context["analysis_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError("analysis_id must be a positive integer") from exc
        if analysis_id <= 0:
            raise ValueError("analysis_id must be a positive integer")
        return analysis_id

    def _context_analysis_id(self, context: Optional[Dict[str, Any]]) -> int:
        try:
            return int((context or {}).get("analysis_id", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _normalise_outputs(
        self,
        outputs: Any,
    ) -> Dict[str, AgentOutput]:
        if not isinstance(outputs, dict):
            return {}

        name_to_key = {
            "Financial Agent": "financial",
            "Marketing Agent": "marketing",
            "Legal Agent": "legal",
        }
        normalised: Dict[str, AgentOutput] = {}
        for key, raw in outputs.items():
            try:
                output = self._coerce_output(raw)
            except Exception:
                continue

            agent_key = key
            if agent_key not in {"financial", "marketing", "legal"}:
                agent_key = name_to_key.get(output.agent_name, key)

            # Preserve an existing key if it was already supplied by name.
            if agent_key in normalised:
                continue
            normalised[agent_key] = output
        return normalised

    def _load_evidence(
        self,
        analysis_id: int,
        startup_id: int,
    ) -> Dict[int, Evidence]:
        if self.db is None:
            raise ValueError("A database session is required to load evidence")

        query = self.db.query(Evidence).filter(
            Evidence.analysis_id == analysis_id
        )
        if startup_id:
            query = query.filter(Evidence.startup_id == startup_id)
        return {item.id: item for item in query.all()}

    def _build_output(
        self,
        analysis_id: int,
        outputs: Dict[str, AgentOutput],
        specialist_errors: Dict[str, Any],
        evidence_by_id: Dict[int, Evidence],
    ) -> VerificationOutput:
        claim_reviews: List[VerificationClaimReview] = []
        unsupported_claims: List[str] = []
        missing_evidence: List[str] = []
        issues: List[str] = []
        specialist_statuses: Dict[str, str] = {}

        checked_references = 0
        valid_references = 0
        invalid_references = 0
        total_findings = 0

        for agent_key, error in specialist_errors.items():
            specialist_statuses[agent_key] = "FAILED"
            missing_evidence.append(f"{agent_key}: {error}")
            issues.append(f"{agent_key}: {error}")

        source_reliability = [
            self._assess_source(evidence)
            for evidence in evidence_by_id.values()
        ]

        for agent_key, output in outputs.items():
            specialist_statuses[agent_key] = output.execution_status.value
            if output.error_details:
                issues.append(f"{agent_key}: {output.error_details}")

            for finding in output.findings:
                total_findings += 1
                references = list(finding.evidence_references or [])
                checked_references += len(references)

                missing_refs = [
                    evidence_id
                    for evidence_id in references
                    if evidence_id not in evidence_by_id
                ]
                valid_refs = [
                    evidence_id
                    for evidence_id in references
                    if evidence_id in evidence_by_id
                ]
                invalid_references += len(missing_refs)
                valid_references += len(valid_refs)

                stored_status = self._aggregate_status(
                    self._normalise_status(
                        evidence_by_id[evidence_id].verification_status
                    )
                    for evidence_id in valid_refs
                )
                if not valid_refs:
                    stored_status = (
                        EvidenceStatus.UNAVAILABLE
                        if not references
                        else EvidenceStatus.UNAVAILABLE
                    )

                claim_status = self._claim_status(
                    finding,
                    references,
                    missing_refs,
                    stored_status,
                )

                supporting_refs = [
                    self._reference(evidence_by_id[evidence_id])
                    for evidence_id in valid_refs
                ]
                reasoning = self._claim_reasoning(
                    finding,
                    references,
                    missing_refs,
                    stored_status,
                    claim_status,
                )

                review = VerificationClaimReview(
                    agent_key=agent_key,
                    agent_name=output.agent_name,
                    dimension=finding.dimension,
                    claim=finding.summary,
                    risk_level=finding.risk_level,
                    claimed_evidence_status=finding.evidence_status,
                    verified_evidence_status=stored_status,
                    verification_status=claim_status,
                    supporting_evidence_ids=valid_refs,
                    supporting_evidence=supporting_refs,
                    reasoning=reasoning,
                )
                claim_reviews.append(review)

                is_missing_dimension = (
                    "missing" in finding.dimension.lower()
                    or finding.dimension.lower().startswith("missing")
                )
                if (
                    not is_missing_dimension
                    and finding.evidence_status != EvidenceStatus.UNAVAILABLE
                    and claim_status in {
                        VerificationStatus.UNVERIFIED,
                        VerificationStatus.UNAVAILABLE,
                        VerificationStatus.CONTRADICTED,
                    }
                ):
                    unsupported_claims.append(
                        f"{output.agent_name} - {finding.dimension}: "
                        f"{finding.summary}"
                    )
                if missing_refs and f"{output.agent_name} - {finding.dimension}: {finding.summary}" not in unsupported_claims:
                    unsupported_claims.append(
                        f"{output.agent_name} - {finding.dimension}: "
                        f"{finding.summary}"
                    )

                if missing_refs:
                    missing_evidence.append(
                        f"{output.agent_name}/{finding.dimension}: references "
                        "evidence that does not belong to this analysis: "
                        + ", ".join(str(item) for item in missing_refs)
                    )
                if finding.evidence_status != EvidenceStatus.UNAVAILABLE and not references:
                    missing_evidence.append(
                        f"{output.agent_name}/{finding.dimension}: no stored "
                        "evidence reference supports this claim."
                    )
                if finding.evidence_status == EvidenceStatus.UNAVAILABLE:
                    missing_evidence.append(
                        f"{output.agent_name}/{finding.dimension}: no supporting "
                        "evidence was found in the retrieved evidence set."
                    )

                if (
                    _STATUS_ORDER[finding.evidence_status]
                    > _STATUS_ORDER[stored_status]
                    and valid_refs
                ):
                    issues.append(
                        f"{finding.dimension} claims "
                        f"{finding.evidence_status.value} evidence but stored "
                        f"evidence is {stored_status.value}."
                    )

                for evidence_id in references:
                    if evidence_id not in evidence_by_id:
                        issues.append(
                            f"{finding.dimension} references evidence "
                            f"{evidence_id}, which does not belong to analysis "
                            f"{analysis_id}."
                        )
                    else:
                        reference_status = next(
                            (
                                reference.verification_status
                                for reference in output.evidence_references
                                if reference.evidence_id == evidence_id
                            ),
                            None,
                        )
                        stored_ref_status = self._normalise_status(
                            evidence_by_id[evidence_id].verification_status
                        )
                        if (
                            reference_status is not None
                            and reference_status != stored_ref_status
                        ):
                            issues.append(
                                f"{finding.dimension} reference "
                                f"{evidence_id} reports "
                                f"{reference_status.value} but stored evidence "
                                f"is {stored_ref_status.value}."
                            )

            for item in output.missing_information or []:
                missing_evidence.append(f"{output.agent_name}: {item}")

        contradictions = self._detect_contradictions(
            outputs,
            claim_reviews,
            evidence_by_id,
        )
        for contradiction in contradictions:
            issues.append(f"Contradiction: {contradiction.reasoning}")

        # Mark claim reviews that participate in a contradiction.
        contradicted_keys = {
            (review.agent_key, review.dimension)
            for review in claim_reviews
            if any(
                review.agent_name in contradiction.agents
                and review.dimension in (contradiction.dimension or review.dimension)
                for contradiction in contradictions
            )
        }
        # A more precise match: contradictions store claim text, so match by claim.
        contradicted_claims = {contradiction.claim_a for contradiction in contradictions}
        contradicted_claims.update(
            contradiction.claim_b for contradiction in contradictions
        )
        for review in claim_reviews:
            if review.claim in contradicted_claims:
                review.verification_status = VerificationStatus.CONTRADICTED
                if review.claim not in unsupported_claims:
                    unsupported_claims.append(
                        f"{review.agent_name} - {review.dimension}: "
                        f"{review.claim}"
                    )

        if not outputs:
            issues.append("No specialist outputs were available to verify.")
            missing_evidence.append(
                "No specialist outputs were available to verify."
            )

        overall_status = self._overall_status(claim_reviews, contradictions, valid_references)
        if contradictions:
            overall_status = VerificationStatus.CONTRADICTED

        supported_count = sum(
            1
            for review in claim_reviews
            if review.verification_status == VerificationStatus.VERIFIED
        )
        detailed_reasoning = self._detailed_reasoning(
            claim_reviews,
            checked_references,
            valid_references,
            invalid_references,
            unsupported_claims,
            contradictions,
            missing_evidence,
            overall_status,
        )
        investor_impact = self._investor_impact(
            overall_status,
            supported_count,
            len(claim_reviews),
            len(unsupported_claims),
            len(contradictions),
            len(missing_evidence),
        )

        execution_status = ExecutionStatus.SUCCESS
        if not outputs:
            execution_status = ExecutionStatus.FAILED
        elif unsupported_claims or contradictions or missing_evidence or issues:
            execution_status = ExecutionStatus.PARTIAL

        deduped_missing = []
        seen_missing = set()
        for item in missing_evidence:
            if item in seen_missing:
                continue
            seen_missing.add(item)
            deduped_missing.append(item)
        missing_evidence = deduped_missing

        all_supporting = []
        seen_refs = set()
        for review in claim_reviews:
            for reference in review.supporting_evidence:
                if reference.evidence_id in seen_refs:
                    continue
                seen_refs.add(reference.evidence_id)
                all_supporting.append(reference)

        return VerificationOutput(
            analysis_id=analysis_id,
            execution_status=execution_status,
            status=overall_status,
            verification_status=overall_status,
            total_findings=total_findings,
            checked_references=checked_references,
            valid_references=valid_references,
            invalid_references=invalid_references,
            claims_reviewed=claim_reviews,
            supporting_evidence=all_supporting,
            unsupported_claims=unsupported_claims,
            contradictions=contradictions,
            source_reliability=source_reliability,
            missing_evidence=missing_evidence,
            detailed_reasoning=detailed_reasoning,
            investor_impact=investor_impact,
            results=claim_reviews,
            issues=issues,
            specialist_statuses=specialist_statuses,
            error_details=None,
        )

    def _coerce_output(self, output: Any) -> AgentOutput:
        if isinstance(output, AgentOutput):
            return output
        if isinstance(output, dict):
            return AgentOutput.model_validate(output)
        raise TypeError(f"Unsupported agent output type: {type(output).__name__}")

    def _claim_status(
        self,
        finding: Any,
        references: List[int],
        missing_refs: List[int],
        stored_status: EvidenceStatus,
    ) -> VerificationStatus:
        if not references:
            if finding.evidence_status == EvidenceStatus.UNAVAILABLE:
                return VerificationStatus.UNAVAILABLE
            return VerificationStatus.UNVERIFIED

        if missing_refs:
            return VerificationStatus.UNAVAILABLE

        if stored_status == EvidenceStatus.UNAVAILABLE:
            return VerificationStatus.UNAVAILABLE

        if _STATUS_ORDER[finding.evidence_status] > _STATUS_ORDER[stored_status]:
            return VerificationStatus(stored_status.value)

        if stored_status == EvidenceStatus.VERIFIED:
            return VerificationStatus.VERIFIED
        if stored_status == EvidenceStatus.PARTIALLY_VERIFIED:
            return VerificationStatus.PARTIALLY_VERIFIED
        return VerificationStatus.UNVERIFIED

    def _claim_reasoning(
        self,
        finding: Any,
        references: List[int],
        missing_refs: List[int],
        stored_status: EvidenceStatus,
        claim_status: VerificationStatus,
    ) -> str:
        if not references:
            if finding.evidence_status == EvidenceStatus.UNAVAILABLE:
                return (
                    "The specialist explicitly reported this dimension as "
                    "unavailable, and no stored evidence contradicts that."
                )
            return (
                "The claim asserts supporting evidence but no evidence references "
                "were supplied, so it cannot be verified."
            )

        if missing_refs:
            return (
                "Some referenced evidence IDs are not present in stored evidence "
                "for this analysis, so the claim is not verifiable."
            )

        if _STATUS_ORDER[finding.evidence_status] > _STATUS_ORDER[stored_status]:
            return (
                f"The claim states {finding.evidence_status.value} evidence, but "
                f"the stored evidence is {stored_status.value}; the claim is "
                "overstated relative to the available evidence."
            )

        if claim_status == VerificationStatus.VERIFIED:
            return (
                "All referenced evidence exists in stored evidence and its "
                "verification status supports the claim."
            )
        if claim_status == VerificationStatus.PARTIALLY_VERIFIED:
            return (
                "The referenced evidence exists, but only part of it is verified."
            )
        if claim_status == VerificationStatus.UNAVAILABLE:
            return "The referenced evidence is unavailable in stored evidence."
        return "The referenced evidence exists but is currently unverified."

    def _detect_contradictions(
        self,
        outputs: Dict[str, AgentOutput],
        claim_reviews: List[VerificationClaimReview],
        evidence_by_id: Dict[int, Evidence],
    ) -> List[VerificationContradiction]:
        contradictions: List[VerificationContradiction] = []
        seen = set()

        def add(contradiction: VerificationContradiction) -> None:
            key = (
                tuple(sorted(contradiction.agents)),
                contradiction.claim_a,
                contradiction.claim_b,
            )
            if key in seen:
                return
            seen.add(key)
            contradictions.append(contradiction)

        agent_risks = {
            key: output.risk_level for key, output in outputs.items()
        }
        if len(agent_risks) >= 2:
            highest = max(agent_risks.values(), key=lambda risk: _RISK_ORDER[risk])
            lowest = min(agent_risks.values(), key=lambda risk: _RISK_ORDER[risk])
            if _RISK_ORDER[highest] - _RISK_ORDER[lowest] >= 3:
                high_agents = [
                    key for key, risk in agent_risks.items() if risk == highest
                ]
                low_agents = [
                    key for key, risk in agent_risks.items() if risk == lowest
                ]
                add(
                    VerificationContradiction(
                        agents=sorted(set(high_agents + low_agents)),
                        claim_a=(
                            f"{', '.join(high_agents)} assessed overall risk as "
                            f"{highest.value}."
                        ),
                        claim_b=(
                            f"{', '.join(low_agents)} assessed overall risk as "
                            f"{lowest.value}."
                        ),
                        severity=highest,
                        reasoning=(
                            "Specialist agents produced materially different "
                            "overall risk assessments."
                        ),
                    )
                )

        by_evidence: Dict[int, List[VerificationClaimReview]] = defaultdict(list)
        for review in claim_reviews:
            for evidence_id in review.supporting_evidence_ids:
                by_evidence[evidence_id].append(review)

        opposite_terms = (
            ("profitable", "unprofitable"),
            ("profitable", "net loss"),
            ("debt-free", "high debt"),
            ("debt free", "significant liabilities"),
            ("no outstanding debt", "debt"),
            ("registered", "not registered"),
            ("registered", "struck off"),
            ("compliant", "non-compliance"),
            ("compliant", "breach"),
        )

        for evidence_id, reviews in by_evidence.items():
            agents = {review.agent_key for review in reviews}
            if len(agents) < 2:
                continue

            statuses = {review.claimed_evidence_status for review in reviews}
            risks = {review.risk_level for review in reviews}
            risk_spread = (
                max((_RISK_ORDER[risk] for risk in risks), default=0)
                - min((_RISK_ORDER[risk] for risk in risks), default=0)
            )
            if len(statuses) > 1 or risk_spread >= 2:
                add(
                    VerificationContradiction(
                        agents=sorted(agents),
                        claim_a=reviews[0].claim,
                        claim_b=reviews[1].claim,
                        evidence_ids=[evidence_id],
                        severity=max(risks, key=lambda risk: _RISK_ORDER[risk]),
                        reasoning=(
                            f"Agents interpreted the same stored evidence "
                            f"(id {evidence_id}) differently."
                        ),
                    )
                )

            for first, second in [
                (reviews[i], reviews[j])
                for i in range(len(reviews))
                for j in range(i + 1, len(reviews))
            ]:
                text_first = f"{first.claim} {first.reasoning}".lower()
                text_second = f"{second.claim} {second.reasoning}".lower()
                for positive, negative in opposite_terms:
                    if (
                        positive in text_first
                        and negative in text_second
                    ) or (
                        negative in text_first
                        and positive in text_second
                    ):
                        add(
                            VerificationContradiction(
                                agents=sorted({first.agent_key, second.agent_key}),
                                claim_a=first.claim,
                                claim_b=second.claim,
                                evidence_ids=[evidence_id],
                                severity=max(
                                    first.risk_level,
                                    second.risk_level,
                                    key=lambda risk: _RISK_ORDER[risk],
                                ),
                                reasoning=(
                                    "Claims that share stored evidence contain "
                                    "opposing terms."
                                ),
                            )
                        )

        return contradictions

    def _assess_source(self, evidence: Evidence) -> SourceReliabilityAssessment:
        status = self._normalise_status(evidence.verification_status)
        score = 0.0
        factors: List[str] = []

        if status == EvidenceStatus.VERIFIED:
            score += 0.55
            factors.append("stored verification status is VERIFIED")
        elif status == EvidenceStatus.PARTIALLY_VERIFIED:
            score += 0.35
            factors.append("stored verification status is PARTIALLY_VERIFIED")
        elif status == EvidenceStatus.UNVERIFIED:
            score += 0.05
            factors.append("stored verification status is UNVERIFIED")
        else:
            factors.append("stored verification status is UNAVAILABLE")

        if getattr(evidence, "content_hash", None):
            score += 0.15
            factors.append("content hash is recorded")
        if getattr(evidence, "source_title", None):
            score += 0.05
            factors.append("source title is recorded")
        extracted = getattr(evidence, "extracted_information", "") or ""
        if len(str(extracted)) >= 80:
            score += 0.10
            factors.append("extracted text is sufficiently detailed")
        metadata = getattr(evidence, "source_metadata", {}) or {}
        if metadata.get("demonstration_data"):
            factors.append("record is labelled demonstration data")
        if not metadata.get("demonstration_data"):
            score += 0.05
            factors.append("record is not labelled demonstration data")

        score = min(1.0, round(score, 2))
        if score >= 0.75:
            level = "HIGH"
        elif score >= 0.45:
            level = "MEDIUM"
        elif score > 0:
            level = "LOW"
        else:
            level = "UNAVAILABLE"

        return SourceReliabilityAssessment(
            evidence_id=evidence.id,
            source_title=evidence.source_title,
            source_url=evidence.source_url,
            verification_status=status,
            reliability_score=score,
            reliability_level=level,
            factors=factors,
        )

    def _aggregate_status(self, statuses) -> EvidenceStatus:
        values = list(statuses)
        if not values:
            return EvidenceStatus.UNAVAILABLE
        if all(status == EvidenceStatus.VERIFIED for status in values):
            return EvidenceStatus.VERIFIED
        if any(
            status in {EvidenceStatus.VERIFIED, EvidenceStatus.PARTIALLY_VERIFIED}
            for status in values
        ):
            return EvidenceStatus.PARTIALLY_VERIFIED
        if any(status == EvidenceStatus.UNVERIFIED for status in values):
            return EvidenceStatus.UNVERIFIED
        return EvidenceStatus.UNAVAILABLE

    def _normalise_status(self, value: Any) -> EvidenceStatus:
        if isinstance(value, EvidenceStatus):
            return value
        normalised = str(value or "").strip().upper()
        try:
            return EvidenceStatus(normalised)
        except ValueError:
            return EvidenceStatus.UNVERIFIED

    def _reference(self, evidence: Evidence) -> EvidenceReference:
        excerpt = str(
            getattr(evidence, "extracted_information", "")
            or getattr(evidence, "raw_text", "")
            or ""
        ).strip()
        if len(excerpt) > 280:
            excerpt = excerpt[:277].rsplit(" ", 1)[0] + "..."
        return EvidenceReference(
            evidence_id=evidence.id,
            source_url=evidence.source_url,
            source_title=evidence.source_title,
            source_category=evidence.source_category,
            verification_status=self._normalise_status(
                evidence.verification_status
            ),
            excerpt=excerpt,
        )

    def _overall_status(
        self,
        claim_reviews: List[VerificationClaimReview],
        contradictions: List[VerificationContradiction],
        valid_references: int,
    ) -> VerificationStatus:
        if contradictions:
            return VerificationStatus.CONTRADICTED
        if not claim_reviews or valid_references == 0:
            if claim_reviews and any(
                review.verified_evidence_status != EvidenceStatus.UNAVAILABLE
                for review in claim_reviews
            ):
                pass
            return VerificationStatus.UNAVAILABLE

        statuses = [review.verification_status for review in claim_reviews]
        if all(status == VerificationStatus.VERIFIED for status in statuses):
            return VerificationStatus.VERIFIED
        if any(
            status == VerificationStatus.VERIFIED for status in statuses
        ) and any(
            status in {
                VerificationStatus.UNVERIFIED,
                VerificationStatus.PARTIALLY_VERIFIED,
                VerificationStatus.UNAVAILABLE,
            }
            for status in statuses
        ):
            return VerificationStatus.PARTIALLY_VERIFIED
        if any(status == VerificationStatus.PARTIALLY_VERIFIED for status in statuses):
            return VerificationStatus.PARTIALLY_VERIFIED
        if any(status == VerificationStatus.UNVERIFIED for status in statuses):
            return VerificationStatus.UNVERIFIED
        return VerificationStatus.UNAVAILABLE

    def _detailed_reasoning(
        self,
        claim_reviews: List[VerificationClaimReview],
        checked_references: int,
        valid_references: int,
        invalid_references: int,
        unsupported_claims: List[str],
        contradictions: List[VerificationContradiction],
        missing_evidence: List[str],
        overall_status: VerificationStatus,
    ) -> str:
        if not claim_reviews:
            return (
                "No specialist claims were available for verification. The "
                "Verification Agent cannot verify findings without specialist "
                "output and stored evidence."
            )

        return (
            f"Reviewed {len(claim_reviews)} specialist claim(s). "
            f"{valid_references} of {checked_references} evidence reference(s) "
            f"were found in stored evidence; {invalid_references} reference(s) "
            f"were invalid. {len(unsupported_claims)} claim(s) are unsupported "
            f"or overstated, {len(contradictions)} contradiction(s) were "
            f"detected, and {len(missing_evidence)} missing-evidence item(s) "
            f"were recorded. Overall verification status: "
            f"{overall_status.value}."
        )

    def _investor_impact(
        self,
        overall_status: VerificationStatus,
        supported_count: int,
        total_claims: int,
        unsupported_count: int,
        contradiction_count: int,
        missing_count: int,
    ) -> str:
        if contradiction_count:
            lead = (
                "Specialist findings conflict and must be reconciled before "
                "they can support an investment decision."
            )
        elif overall_status == VerificationStatus.VERIFIED:
            lead = (
                "All reviewed claims are supported by stored evidence, but this "
                "is still not independent verification."
            )
        elif overall_status == VerificationStatus.PARTIALLY_VERIFIED:
            lead = (
                "Some claims are supported by stored evidence, while others "
                "require corroboration."
            )
        elif overall_status == VerificationStatus.UNVERIFIED:
            lead = (
                "The available stored evidence does not yet substantiate the "
                "specialist claims."
            )
        elif overall_status == VerificationStatus.CONTRADICTED:
            lead = (
                "Conflicting specialist findings prevent a reliable diligence "
                "conclusion."
            )
        else:
            lead = (
                "Insufficient evidence is available to verify the specialist "
                "findings."
            )

        return (
            f"{lead} {supported_count} of {total_claims} claim(s) are verified; "
            f"{unsupported_count} are unsupported or overstated; "
            f"{missing_count} missing-evidence item(s) are recorded."
        )

    def _error_output(
        self,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> VerificationOutput:
        return VerificationOutput(
            analysis_id=self._context_analysis_id(context),
            execution_status=ExecutionStatus.FAILED,
            status=VerificationStatus.UNAVAILABLE,
            verification_status=VerificationStatus.UNAVAILABLE,
            issues=["Verification could not be completed."],
            missing_evidence=["Verification could not be completed."],
            detailed_reasoning="Verification could not be completed due to an execution error.",
            investor_impact=(
                "No verification conclusion can be drawn because the verification "
                "process encountered an execution error."
            ),
            error_details=str(error),
        )

# Backwards-compatible alias for the earlier finding model.
VerificationFinding = VerificationClaimReview

