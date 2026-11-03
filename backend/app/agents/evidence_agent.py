import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.output import (
    AgentFinding,
    AgentOutput,
    EvidenceReference,
    EvidenceStatus,
    ExecutionStatus,
    RiskLevel,
)
from app.db.models import Evidence

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

_RISK_ORDER = {
    RiskLevel.UNKNOWN: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


@dataclass(frozen=True)
class DimensionSpec:
    name: str
    keywords: Tuple[str, ...]
    risk_terms: Tuple[str, ...] = ()
    critical_terms: Tuple[str, ...] = ()
    preferred_categories: Tuple[str, ...] = ()


@dataclass(frozen=True)
class _Match:
    evidence: Any
    text: str
    snippet: str
    score: int


class EvidenceAgent(BaseAgent):
    """Evidence-backed agent that never infers unavailable facts.

    The agent only quotes or summarises retrieved evidence. Missing fields are
    reported as gaps rather than estimated values, and the highest possible
    verification state is the verification state of the underlying evidence.
    """

    AGENT_NAME = "Evidence Agent"
    MISSING_LABEL = "Missing information"
    RELEVANT_CATEGORIES: Tuple[str, ...] = ()
    DIMENSION_SPECS: Tuple[DimensionSpec, ...] = ()
    CAVEAT = (
        "Conclusions are limited to the retrieved public evidence and do not "
        "constitute independent verification."
    )

    def __init__(self, db: Optional[Session] = None) -> None:
        super().__init__(self.AGENT_NAME)
        self.db = db

    async def run(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentOutput:
        try:
            analysis_id = self._analysis_id(context)
            evidence = self._load_evidence(startup_id, analysis_id, context)
            return self._build_output(analysis_id, evidence)
        except Exception as exc:
            self.logger.error(f"Agent {self.name} failed: {exc}")
            return self._error_output(context, exc)

    def structured_error_output(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> AgentOutput:
        return self._error_output(context, error)

    def _analysis_id(self, context: Optional[Dict[str, Any]]) -> int:
        if not context or context.get("analysis_id") is None:
            raise ValueError(
                "analysis_id is required in the agent context so findings can "
                "be linked to an analysis."
            )
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

    def _load_evidence(
        self,
        startup_id: int,
        analysis_id: int,
        context: Optional[Dict[str, Any]],
    ) -> List[Evidence]:
        supplied = (context or {}).get("evidence")
        if supplied is not None:
            evidence = list(supplied)
        else:
            if self.db is None:
                raise ValueError("A database session is required to load evidence")

            query = self.db.query(Evidence).filter(
                Evidence.analysis_id == analysis_id
            )
            if startup_id:
                query = query.filter(Evidence.startup_id == startup_id)
            evidence = (
                query.order_by(Evidence.retrieval_date.desc(), Evidence.id.desc())
                .all()
            )

        if self.RELEVANT_CATEGORIES:
            evidence = [
                item
                for item in evidence
                if str(
                    self._evidence_value(item, "source_category") or ""
                ).lower()
                in self.RELEVANT_CATEGORIES
            ]
        return evidence

    def _build_output(
        self,
        analysis_id: int,
        evidence: Sequence[Evidence],
    ) -> AgentOutput:
        findings: List[AgentFinding] = []
        detailed: Dict[str, str] = {}
        risk_levels: Dict[str, RiskLevel] = {}
        references: Dict[int, EvidenceReference] = {}
        missing_information: List[str] = []

        for spec in self.DIMENSION_SPECS:
            matches = self._match_dimension(spec, evidence)
            if matches:
                status = self._evidence_status(match.evidence for match in matches)
                risk = self._risk_for(spec, matches, status)
                refs = []
                for match in matches:
                    evidence_id = self._evidence_value(match.evidence, "id")
                    refs.append(evidence_id)
                    references.setdefault(
                        evidence_id,
                        self._reference(match.evidence, match.snippet),
                    )
                summary = (
                    f"{len(matches)} evidence source(s) directly reference "
                    f"{spec.name.lower()}. Key evidence: \"{matches[0].snippet}\""
                )
                explanation = (
                    f"{spec.name}: The retrieved source(s) "
                    f"{self._source_list(matches)} state: "
                    f"{self._snippet_list(matches)}. {self.CAVEAT}"
                )
                finding = AgentFinding(
                    dimension=spec.name,
                    summary=summary,
                    explanation=explanation,
                    risk_level=risk,
                    evidence_status=status,
                    evidence_references=refs,
                    investor_impact=self._investor_impact(risk, status, spec.name),
                )
            else:
                status = EvidenceStatus.UNAVAILABLE
                risk = RiskLevel.UNKNOWN
                explanation = (
                    f"{spec.name}: No retrieved source directly addresses this "
                    "dimension. This is a documentation gap, not evidence that "
                    f"the risk is absent. {self.CAVEAT}"
                )
                finding = AgentFinding(
                    dimension=spec.name,
                    summary=(
                        f"No supporting evidence was found for "
                        f"{spec.name.lower()} in the current evidence set."
                    ),
                    explanation=explanation,
                    risk_level=RiskLevel.UNKNOWN,
                    evidence_status=EvidenceStatus.UNAVAILABLE,
                    evidence_references=[],
                    investor_impact=self._investor_impact(
                        RiskLevel.UNKNOWN,
                        EvidenceStatus.UNAVAILABLE,
                        spec.name,
                    ),
                )
                missing_information.append(
                    f"{spec.name}: no supporting evidence was found."
                )

            findings.append(finding)
            detailed[spec.name] = finding.explanation
            risk_levels[spec.name] = finding.risk_level

        assessed = list(findings)
        overall_status = self._overall_status(assessed, evidence)
        overall_risk = self._overall_risk(assessed)

        missing_summary = (
            "No evidence gaps were detected across the requested dimensions in "
            "the retrieved evidence set."
            if not missing_information
            else "Evidence was unavailable for: "
            + ", ".join(
                item.split(":", 1)[0] for item in missing_information
            )
            + "."
        )
        missing_finding = AgentFinding(
            dimension=self.MISSING_LABEL,
            summary=missing_summary,
            explanation=(
                f"{missing_summary} Missing information is reported explicitly "
                "and is not estimated. "
                + self.CAVEAT
            ),
            risk_level=RiskLevel.UNKNOWN,
            evidence_status=(
                EvidenceStatus.UNAVAILABLE
                if missing_information
                else EvidenceStatus.UNVERIFIED
            ),
            evidence_references=[],
            investor_impact=(
                "Request the missing primary documentation before relying on "
                "this analysis."
                if missing_information
                else "The retrieved evidence set covers the requested dimensions, "
                "but source verification may still be required."
            ),
        )
        findings.append(missing_finding)
        detailed[self.MISSING_LABEL] = missing_finding.explanation
        risk_levels[self.MISSING_LABEL] = missing_finding.risk_level

        if overall_status != EvidenceStatus.VERIFIED:
            missing_information.append(
                "Independent verification of the cited public sources has not "
                "been completed."
            )

        execution_status = (
            ExecutionStatus.PARTIAL
            if missing_information
            else ExecutionStatus.SUCCESS
        )
        investor_impact = self._overall_investor_impact(
            overall_risk,
            overall_status,
            len(missing_information),
            self._analysed_dimension_count(assessed),
        )

        return AgentOutput(
            agent_name=self.name,
            analysis_id=analysis_id,
            findings=findings,
            detailed_explanations=detailed,
            evidence_references=list(references.values()),
            risk_level=overall_risk,
            risk_levels=risk_levels,
            evidence_status=overall_status,
            investor_impact=investor_impact,
            missing_information=missing_information,
            execution_status=execution_status,
            error_details=None,
        )

    def _match_dimension(
        self,
        spec: DimensionSpec,
        evidence: Sequence[Evidence],
    ) -> List[_Match]:
        matches: List[_Match] = []
        for item in evidence:
            text = self._evidence_text(item)
            lowered = text.lower()
            hits = [keyword for keyword in spec.keywords if keyword in lowered]
            if not hits:
                continue

            category = str(
                self._evidence_value(item, "source_category") or ""
            ).lower()
            title = str(self._evidence_value(item, "source_title") or "")
            score = len(hits)
            if category in spec.preferred_categories:
                score += 2
            if any(keyword in title.lower() for keyword in hits):
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

    def _evidence_value(
        self,
        evidence: Any,
        field: str,
        default: Any = "",
    ) -> Any:
        if isinstance(evidence, dict):
            return evidence.get(field, default)
        return getattr(evidence, field, default)

    def _evidence_text(self, evidence: Any) -> str:
        title = str(self._evidence_value(evidence, "source_title") or "")
        extracted = str(
            self._evidence_value(evidence, "extracted_information") or ""
        )
        raw_text = str(self._evidence_value(evidence, "raw_text") or "")

        if extracted and raw_text:
            if extracted in raw_text or raw_text in extracted:
                raw_text = ""

        parts = [title, extracted, raw_text]
        return "\n".join(part for part in parts if part)

    def _best_snippet(self, text: str, keywords: Sequence[str]) -> str:
        sentences = [
            sentence.strip()
            for sentence in _SENTENCE_SPLIT.split(text)
            if len(sentence.strip()) >= 20
        ]
        lowered_keywords = [keyword.lower() for keyword in keywords]
        matching = [
            sentence
            for sentence in sentences
            if any(keyword in sentence.lower() for keyword in lowered_keywords)
        ]
        choices = matching or sentences
        if not choices:
            return text.strip()[:300]
        snippet = " ".join(choices[:2])
        if len(snippet) > 360:
            snippet = snippet[:357].rsplit(" ", 1)[0] + "..."
        return snippet

    def _source_list(self, matches: Sequence[_Match]) -> str:
        titles = []
        seen = set()
        for match in matches:
            title = self._evidence_value(
                match.evidence, "source_title"
            ) or self._evidence_value(match.evidence, "source_url")
            if title not in seen:
                seen.add(title)
                titles.append(title)
        return ", ".join(titles)

    def _snippet_list(self, matches: Sequence[_Match]) -> str:
        snippets = []
        seen = set()
        for match in matches:
            if match.snippet in seen:
                continue
            seen.add(match.snippet)
            snippets.append(f"\"{match.snippet}\"")
            if len(snippets) == 2:
                break
        return "; ".join(snippets)

    def _reference(self, evidence: Any, excerpt: str) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=self._evidence_value(evidence, "id"),
            source_url=self._evidence_value(evidence, "source_url"),
            source_title=self._evidence_value(evidence, "source_title"),
            source_category=self._evidence_value(evidence, "source_category"),
            verification_status=self._normalise_status(
                self._evidence_value(evidence, "verification_status")
            ),
            excerpt=excerpt,
        )

    def _evidence_status(
        self,
        evidence: Sequence[Any],
    ) -> EvidenceStatus:
        statuses = {
            self._normalise_status(
                self._evidence_value(item, "verification_status")
            )
            for item in evidence
        }
        if EvidenceStatus.VERIFIED in statuses:
            return EvidenceStatus.VERIFIED
        if EvidenceStatus.PARTIALLY_VERIFIED in statuses:
            return EvidenceStatus.PARTIALLY_VERIFIED
        if statuses:
            return EvidenceStatus.UNVERIFIED
        return EvidenceStatus.UNAVAILABLE

    def _normalise_status(self, value: str) -> EvidenceStatus:
        normalised = (value or "").strip().upper()
        try:
            return EvidenceStatus(normalised)
        except ValueError:
            return EvidenceStatus.UNVERIFIED

    def _risk_for(
        self,
        spec: DimensionSpec,
        matches: Sequence[_Match],
        status: EvidenceStatus,
    ) -> RiskLevel:
        combined = " ".join(match.text.lower() for match in matches)
        if any(term in combined for term in spec.critical_terms):
            return RiskLevel.CRITICAL
        if any(term in combined for term in spec.risk_terms):
            return RiskLevel.HIGH
        if status == EvidenceStatus.VERIFIED:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def _overall_status(
        self,
        findings: Sequence[AgentFinding],
        evidence: Sequence[Evidence],
    ) -> EvidenceStatus:
        if not evidence:
            return EvidenceStatus.UNAVAILABLE

        statuses = [finding.evidence_status for finding in findings]
        if not statuses:
            return EvidenceStatus.UNAVAILABLE
        if all(status == EvidenceStatus.UNAVAILABLE for status in statuses):
            return EvidenceStatus.UNAVAILABLE
        if all(status == EvidenceStatus.VERIFIED for status in statuses):
            return EvidenceStatus.VERIFIED
        if any(
            status in {EvidenceStatus.VERIFIED, EvidenceStatus.PARTIALLY_VERIFIED}
            for status in statuses
        ):
            return EvidenceStatus.PARTIALLY_VERIFIED
        return EvidenceStatus.UNVERIFIED

    def _overall_risk(self, findings: Sequence[AgentFinding]) -> RiskLevel:
        known = [
            finding.risk_level
            for finding in findings
            if finding.risk_level != RiskLevel.UNKNOWN
        ]
        if not known:
            return RiskLevel.UNKNOWN
        return max(known, key=lambda level: _RISK_ORDER[level])

    def _analysed_dimension_count(
        self,
        findings: Sequence[AgentFinding],
    ) -> int:
        return sum(
            1
            for finding in findings
            if finding.evidence_status != EvidenceStatus.UNAVAILABLE
        )

    def _investor_impact(
        self,
        risk: RiskLevel,
        status: EvidenceStatus,
        dimension: str,
    ) -> str:
        verification = {
            EvidenceStatus.VERIFIED: "The cited evidence is marked as verified.",
            EvidenceStatus.PARTIALLY_VERIFIED: (
                "Only part of the cited evidence is independently verified."
            ),
            EvidenceStatus.UNVERIFIED: (
                "The cited evidence is currently unverified."
            ),
            EvidenceStatus.UNAVAILABLE: "No evidence is available.",
        }[status]

        if risk == RiskLevel.CRITICAL:
            impact = (
                f"Critical diligence concern for {dimension.lower()}; it could "
                "materially affect valuation or investment terms."
            )
        elif risk == RiskLevel.HIGH:
            impact = (
                f"High-risk signal for {dimension.lower()}; request supporting "
                "documents and resolve before relying on it."
            )
        elif risk == RiskLevel.MEDIUM:
            impact = (
                f"Potential diligence concern for {dimension.lower()}; more "
                "evidence is needed before drawing a firm conclusion."
            )
        elif risk == RiskLevel.LOW:
            impact = (
                f"No material adverse signal was found for {dimension.lower()} "
                "in the available evidence."
            )
        else:
            impact = (
                f"{dimension} cannot be assessed from the available evidence."
            )
        return f"{impact} {verification}"

    def _overall_investor_impact(
        self,
        risk: RiskLevel,
        status: EvidenceStatus,
        missing_count: int,
        analysed_dimensions: int,
    ) -> str:
        if risk == RiskLevel.CRITICAL:
            lead = (
                "Critical issues require resolution before an investment "
                "decision can be supported."
            )
        elif risk == RiskLevel.HIGH:
            lead = (
                "Material diligence concerns could affect valuation or deal "
                "terms and require further investigation."
            )
        elif risk == RiskLevel.MEDIUM:
            lead = (
                "Diligence is incomplete and several areas need corroboration "
                "before an investment decision."
            )
        elif risk == RiskLevel.LOW:
            lead = (
                "No material adverse signal was found in the available "
                "evidence, but this is not a substitute for full diligence."
            )
        else:
            lead = (
                "The available evidence is insufficient to support an "
                "investment conclusion."
            )

        return (
            f"{lead} Evidence status: {status.value}. "
            f"{analysed_dimensions} of {len(self.DIMENSION_SPECS)} requested "
            f"dimensions have supporting evidence; {missing_count} missing or "
            "unverified item(s) are recorded."
        )

    def _error_output(
        self,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> AgentOutput:
        missing = [
            f"{spec.name}: analysis could not be completed."
            for spec in self.DIMENSION_SPECS
        ]
        if not missing:
            missing = ["Analysis could not be completed."]

        return AgentOutput(
            agent_name=self.name,
            analysis_id=self._context_analysis_id(context),
            findings=[],
            detailed_explanations={},
            evidence_references=[],
            risk_level=RiskLevel.UNKNOWN,
            risk_levels={},
            evidence_status=EvidenceStatus.UNAVAILABLE,
            investor_impact=(
                "No investment conclusion can be drawn because the analysis "
                "encountered an execution error."
            ),
            missing_information=missing,
            execution_status=ExecutionStatus.FAILED,
            error_details=str(error),
        )
