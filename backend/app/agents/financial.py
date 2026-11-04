"""Evidence-grounded financial assessment and deterministic metric reporting."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agents.evidence_agent import DimensionSpec, EvidenceAgent
from app.agents.output import (
    AgentFinding,
    AgentOutput,
    EvidenceReference,
    EvidenceStatus,
    ExecutionStatus,
    RiskLevel,
)
from app.financial import (
    CalculationKey,
    FinancialCalculationResult,
    FinancialMetricKey,
    FinancialExtractionResult,
    calculate_financial_metrics,
    extract_financials,
)
from app.llm.gateway import LLMResponse, llm_gateway


_DIMENSIONS = (
    "Funding history",
    "Revenue",
    "Profitability",
    "Cash flow",
    "Liquidity",
    "Debt and liabilities",
    "Financial strengths",
    "Financial risks",
)
_MAX_PROMPT_EVIDENCE = 20
_MAX_PROMPT_METRICS = 60
_MAX_PROMPT_CALCULATIONS = 40
_MAX_SOURCE_EXCERPT = 900
_MAX_PROMPT_CHARS = 18_000
_NUMBER_TOKEN = re.compile(r"(?<![A-Za-z])(?:[$€£₹]\s*)?[+-]?\d[\d,]*(?:\.\d+)?\s*%?(?![A-Za-z])")
_NUMBER_WORD = re.compile(r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|half|quarter|dozen)\b", re.I)
_NEGATION = re.compile(r"\b(?:no|not|without|never|none|neither|lack(?:s|ing)?|unable|cannot|can't|didn't|doesn't|isn't|aren't|wasn't|weren't)\b", re.I)
_DIMENSION_METRICS = {
    "Funding history": {
        FinancialMetricKey.FUNDING_RAISED, FinancialMetricKey.FUNDING_ROUND,
        FinancialMetricKey.FUNDING_DATE, FinancialMetricKey.FUNDING_STAGE,
        FinancialMetricKey.NAMED_INVESTORS,
    },
    "Revenue": {FinancialMetricKey.REVENUE},
    "Profitability": {
        FinancialMetricKey.REVENUE, FinancialMetricKey.COST_OF_REVENUE,
        FinancialMetricKey.GROSS_PROFIT, FinancialMetricKey.OPERATING_EXPENSES,
        FinancialMetricKey.OPERATING_INCOME, FinancialMetricKey.EBITDA,
        FinancialMetricKey.NET_INCOME, FinancialMetricKey.NET_LOSS,
    },
    "Cash flow": {
        FinancialMetricKey.REVENUE, FinancialMetricKey.OPERATING_CASH_FLOW,
        FinancialMetricKey.INVESTING_CASH_FLOW, FinancialMetricKey.FINANCING_CASH_FLOW,
        FinancialMetricKey.CAPITAL_EXPENDITURE, FinancialMetricKey.FREE_CASH_FLOW,
    },
    "Liquidity": {
        FinancialMetricKey.CASH_AND_EQUIVALENTS, FinancialMetricKey.CURRENT_ASSETS,
        FinancialMetricKey.CURRENT_LIABILITIES, FinancialMetricKey.TOTAL_ASSETS,
    },
    "Debt and liabilities": {
        FinancialMetricKey.SHORT_TERM_DEBT, FinancialMetricKey.LONG_TERM_DEBT,
        FinancialMetricKey.TOTAL_DEBT, FinancialMetricKey.TOTAL_LIABILITIES,
        FinancialMetricKey.SHAREHOLDERS_EQUITY, FinancialMetricKey.TOTAL_ASSETS,
    },
}
_ALL_METRICS = set(FinancialMetricKey)
_DIMENSION_METRICS["Financial strengths"] = _ALL_METRICS
_DIMENSION_METRICS["Financial risks"] = _ALL_METRICS
_DIMENSION_CALCULATIONS = {
    "Funding history": set(),
    "Revenue": {CalculationKey.ANNUAL_REVENUE_GROWTH},
    "Profitability": {
        CalculationKey.GROSS_PROFIT_MARGIN, CalculationKey.OPERATING_PROFIT_MARGIN,
        CalculationKey.NET_PROFIT_MARGIN, CalculationKey.EBITDA_MARGIN,
    },
    "Cash flow": {
        CalculationKey.OPERATING_CASH_FLOW_MARGIN, CalculationKey.FREE_CASH_FLOW_MARGIN,
        CalculationKey.FREE_CASH_FLOW,
    },
    "Liquidity": {
        CalculationKey.CURRENT_RATIO, CalculationKey.CASH_RATIO,
        CalculationKey.NET_WORKING_CAPITAL,
    },
    "Debt and liabilities": {
        CalculationKey.DEBT_TO_EQUITY_RATIO, CalculationKey.LIABILITIES_TO_ASSETS_RATIO,
    },
}
_ALL_CALCULATIONS = set(CalculationKey)
_DIMENSION_CALCULATIONS["Financial strengths"] = _ALL_CALCULATIONS
_DIMENSION_CALCULATIONS["Financial risks"] = _ALL_CALCULATIONS
_DIMENSION_SUPPORT_TERMS = {
    "Funding history": {"fund", "funding", "raise", "raised", "round", "investor", "seed", "series", "grant", "capital"},
    "Revenue": {"revenue", "sales", "turnover", "arr", "mrr", "booking"},
    "Profitability": {"profit", "profitable", "margin", "ebitda", "income", "loss", "earning", "expense"},
    "Cash flow": {"cash", "flow", "burn", "runway", "capex", "operating", "investing", "financing"},
    "Liquidity": {"liquidity", "cash", "current", "asset", "liability", "working", "ratio"},
    "Debt and liabilities": {"debt", "liability", "loan", "borrow", "obligation", "convertible", "equity", "asset"},
    "Financial strengths": {"revenue", "profit", "cash", "flow", "debt", "liability", "funding", "margin", "asset", "income"},
    "Financial risks": {"revenue", "profit", "cash", "flow", "debt", "liability", "funding", "margin", "risk", "loss", "default", "insolvent"},
}
_CLAIM_TERMS = {
    "revenue", "sales", "turnover", "arr", "mrr", "booking", "profit", "profitable",
    "margin", "ebitda", "income", "loss", "earning", "expense", "cash", "flow", "burn",
    "runway", "capex", "liquidity", "current", "asset", "liability", "debt", "loan",
    "borrow", "obligation", "convertible", "equity", "fund", "funding", "raise", "raised",
    "round", "investor", "seed", "series", "grant", "capital", "growth", "grow", "decline",
    "increase", "decrease", "positive", "negative", "forecast", "actual", "target", "risk",
    "default", "insolvent", "bankruptcy", "working", "ratio", "strong", "weak", "deficit",
    "improve", "improved", "improving", "stable", "deteriorate", "deteriorated", "deteriorating",
    "shortfall", "overdue", "covenant", "concentration", "exposure", "volatility",
    "severe", "significant", "substantial", "rapid", "sharp",
    "double", "doubled", "triple", "tripled", "surge", "surged", "soar", "soared",
    "accelerate", "accelerated", "stagnant", "flat", "worsen", "worsened",
}
_RISK_MARKERS = {"debt", "liability", "loan", "borrow", "loss", "decline", "negative", "burn", "default", "overdue", "insolvent", "bankruptcy", "deficit", "shortfall", "covenant", "risk", "exposure", "weak", "liquidity"}
_HIGH_RISK_MARKERS = {"loss", "decline", "negative", "burn", "default", "overdue", "insolvent", "bankruptcy", "deficit", "shortfall", "covenant", "insufficient"}
_CRITICAL_RISK_MARKERS = {"default", "insolvent", "bankruptcy", "fraud", "going concern"}
_STRENGTH_MARKERS = {"profitable", "profit", "positive", "growth", "grow", "strong", "stable", "margin", "efficient"}
_CLAIM_STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "in", "is", "it", "of", "on", "or", "the", "to", "was", "were", "with", "may", "could", "should", "appears", "indicates", "suggests", "reported", "reports", "report", "source", "evidence", "available", "information", "assessment", "review", "request", "primary", "statement", "statements", "company", "startup", "financial", "item", "items", "supported", "supporting", "support", "supports", "this", "that", "cited", "discuss", "discusses", "states", "describes", "including", "include", "includes", "remains", "remain", "material", "performance", "checked", "records", "limited", "conclusion", "conclusions", "position", "findings", "finding", "history", "calculation", "calculations", "calculated", "uses", "used", "based", "derived", "underlying", "reported", "available", "summary", "overall", "financials", "reviewed", "provides", "provided", "show", "shows", "indicate", "indicating"}


class EvidenceSupport(BaseModel):
    """An exact source excerpt attached to a specific stored evidence record."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(gt=0)
    excerpt: str = Field(min_length=12, max_length=1200)


class FinancialDimensionAssessment(BaseModel):
    """LLM interpretation that can point only to supplied source IDs and keys."""

    model_config = ConfigDict(extra="forbid")

    dimension: str
    summary: str = Field(min_length=1, max_length=1200)
    explanation: str = Field(min_length=1, max_length=3000)
    risk_level: RiskLevel
    evidence_ids: List[int] = Field(default_factory=list)
    supporting_evidence: List["EvidenceSupport"] = Field(default_factory=list)
    metric_keys: List[FinancialMetricKey] = Field(default_factory=list)
    calculation_keys: List[CalculationKey] = Field(default_factory=list)
    investor_impact: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="after")
    def validate_dimension(self):
        if self.dimension not in _DIMENSIONS:
            raise ValueError("unknown financial dimension")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("duplicate evidence ID")
        if len(set(self.metric_keys)) != len(self.metric_keys):
            raise ValueError("duplicate metric key")
        if len(set(self.calculation_keys)) != len(self.calculation_keys):
            raise ValueError("duplicate calculation key")
        return self


class FinancialAssessmentConcern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    dimension: str
    evidence_ids: List[int] = Field(min_length=1)
    supporting_evidence: List["EvidenceSupport"] = Field(min_length=1)
    metric_keys: List[FinancialMetricKey] = Field(default_factory=list)
    calculation_keys: List[CalculationKey] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dimension(self):
        if self.dimension not in _DIMENSIONS:
            raise ValueError("unknown concern dimension")
        return self


class FinancialMissingInformation(BaseModel):
    """Missing items represented only by deterministic Phase 3/4 keys."""

    model_config = ConfigDict(extra="forbid")

    metric_keys: List[FinancialMetricKey] = Field(default_factory=list)
    unavailable_calculation_keys: List[CalculationKey] = Field(default_factory=list)
    ambiguous_calculation_keys: List[CalculationKey] = Field(default_factory=list)


class FinancialAssessmentResponse(BaseModel):
    """Structured, reference-only assessment; it has no fields for new figures."""

    model_config = ConfigDict(extra="forbid")

    overall_summary: str = Field(min_length=1, max_length=2500)
    overall_risk: RiskLevel
    investor_impact: str = Field(min_length=1, max_length=1500)
    key_financial_concerns: List[FinancialAssessmentConcern] = Field(default_factory=list, max_length=20)
    overall_supporting_evidence: List[EvidenceSupport] = Field(default_factory=list)
    missing_information: FinancialMissingInformation = Field(default_factory=FinancialMissingInformation)
    recommended_investor_next_steps: List[str] = Field(default_factory=list, max_length=20)
    dimensions: List[FinancialDimensionAssessment] = Field(min_length=8, max_length=8)

    @model_validator(mode="after")
    def require_all_dimensions_once(self):
        names = [item.dimension for item in self.dimensions]
        if set(names) != set(_DIMENSIONS) or len(set(names)) != len(_DIMENSIONS):
            raise ValueError("response must contain each financial dimension exactly once")
        return self


class FinancialAgent(EvidenceAgent):
    """Financial assessment using extracted evidence and calculated metrics."""

    AGENT_NAME = "Financial Agent"
    MISSING_LABEL = "Missing financial information"
    RELEVANT_CATEGORIES = ("financial", "company")
    CAVEAT = (
        "Public statements are not audited financial statements. Findings are "
        "limited to the cited evidence; no missing financial figure is estimated."
    )
    DIMENSION_SPECS: Tuple[DimensionSpec, ...] = tuple(
        DimensionSpec(name=name, keywords=(), preferred_categories=("financial",))
        for name in _DIMENSIONS
    )

    def __init__(self, db=None, gateway=None) -> None:
        super().__init__(db)
        self.gateway = gateway or llm_gateway

    async def run(self, startup_id: int, context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        try:
            analysis_id = self._analysis_id(context)
            evidence = self._load_evidence(startup_id, analysis_id, context)
            # The database path is analysis-scoped. Apply the same check to
            # caller-supplied context so another analysis cannot be cited.
            evidence = [
                item for item in evidence
                if self._safe_int(self._evidence_value(item, "analysis_id")) == analysis_id
                and (
                    self._evidence_value(item, "startup_id") in (None, "")
                    or self._safe_int(self._evidence_value(item, "startup_id")) == startup_id
                )
            ]
            extraction, calculations, pipeline_error = self._extract_and_calculate(evidence)
            prompt, allowed_ids, metric_provenance, calculation_provenance = self._build_prompt(
                evidence, extraction, calculations
            )
            llm_failure = None
            assessment = None
            try:
                response: LLMResponse = await self.gateway.generate(
                    prompt=prompt,
                    agent_name=self.name,
                    response_schema=FinancialAssessmentResponse,
                )
                if response.provider == "Mock LLM":
                    raise ValueError("Mock provider output is not an assessment")
                assessment = response.parsed
                if assessment is None:
                    raise ValueError("LLM returned no validated financial assessment")
                self._validate_references(
                    assessment,
                    allowed_ids,
                    metric_provenance,
                    calculation_provenance,
                    evidence,
                    set(extraction.missing_metrics),
                    {item.calculation_key for item in calculations.unavailable},
                    {item.calculation_key for item in calculations.ambiguous},
                )
            except Exception as exc:  # Provider or response errors must not stop analysis.
                self.logger.warning(
                    "Financial assessment unavailable (error_type=%s)",
                    type(exc).__name__,
                )
                llm_failure = "LLM interpretation was unavailable or did not pass validation."
                assessment = None

            return self._assemble_output(
                analysis_id,
                evidence,
                extraction,
                calculations,
                assessment,
                llm_failure,
                pipeline_error,
            )
        except Exception as exc:
            self.logger.error("Agent %s failed: %s", self.name, exc)
            return self._error_output(context, exc)

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _extract_and_calculate(
        self, evidence: List[Any]
    ) -> Tuple[FinancialExtractionResult, FinancialCalculationResult, Optional[str]]:
        try:
            extraction = extract_financials(evidence)
        except Exception as exc:  # A single malformed source must not abort the workflow.
            self.logger.warning("Financial extraction failed: %s", exc)
            extraction = FinancialExtractionResult()
            return extraction, FinancialCalculationResult(), "Financial extraction could not process the retrieved evidence."
        try:
            calculations = calculate_financial_metrics(extraction.metrics)
        except Exception as exc:
            self.logger.warning("Financial calculations failed: %s", exc)
            calculations = FinancialCalculationResult()
            return extraction, calculations, "Financial calculations could not be completed."
        return extraction, calculations, None

    def _build_prompt(
        self,
        evidence: List[Any],
        extraction: FinancialExtractionResult,
        calculations: FinancialCalculationResult,
    ) -> Tuple[
        str,
        set[int],
        Dict[FinancialMetricKey, List[Any]],
        Dict[CalculationKey, List[Any]],
    ]:
        source_rows = []
        for item in evidence[:_MAX_PROMPT_EVIDENCE]:
            evidence_id = self._safe_int(self._evidence_value(item, "id"))
            if not evidence_id:
                continue
            text = self._evidence_text(item).strip()[:_MAX_SOURCE_EXCERPT]
            source_rows.append({
                "evidence_id": evidence_id,
                "source_title": str(self._evidence_value(item, "source_title") or "")[:200],
                "text": text,
            })
        allowed_ids = {row["evidence_id"] for row in source_rows}
        metric_rows = []
        for metric in extraction.metrics:
            if metric.source_evidence_id not in allowed_ids:
                continue
            metric_rows.append({
                "source_evidence_id": metric.source_evidence_id,
                "metric_key": metric.metric_key.value,
                "original_metric_label": metric.original_metric_label,
                "normalized_value": str(metric.normalized_value) if metric.normalized_value is not None else None,
                "original_numeric_value": metric.original_numeric_value,
                "text_value": metric.text_value,
                "currency_code": metric.currency_code,
                "currency_symbol": metric.currency_symbol,
                "original_unit_scale": metric.original_unit_scale,
                "normalized_unit": metric.normalized_unit,
                "reporting_period_label": metric.reporting_period_label,
                "period_start_date": metric.period_start_date.isoformat() if metric.period_start_date else None,
                "period_end_date": metric.period_end_date.isoformat() if metric.period_end_date else None,
                "fiscal_year": metric.fiscal_year,
                "fiscal_quarter": metric.fiscal_quarter,
                "statement_type": metric.statement_type.value,
                "extraction_status": metric.extraction_status.value,
                "actuality": metric.actuality,
                "evidence_verification_status": metric.evidence_verification_status,
                "pdf_page_references": metric.pdf_page_references,
                "supporting_excerpt": metric.supporting_excerpt[:320],
            })
            if len(metric_rows) >= _MAX_PROMPT_METRICS:
                break
        calculations_all = (
            calculations.calculated + calculations.unavailable + calculations.ambiguous
        )
        calculation_rows = []
        for item in calculations_all:
            if not item.source_evidence_ids or not set(item.source_evidence_ids).issubset(allowed_ids):
                continue
            calculation_rows.append({
                "calculation_key": item.calculation_key.value,
                "calculation_name": item.calculation_name,
                "value": str(item.value) if item.value is not None else None,
                "unit": item.unit.value,
                "formula": item.formula,
                "status": item.status.value,
                "explanation": item.explanation,
                "source_evidence_ids": item.source_evidence_ids,
                "input_metrics": [
                    {
                        "metric_key": value.metric_key.value,
                        "source_evidence_id": value.source_evidence_id,
                        "supporting_excerpt": value.supporting_excerpt[:320],
                        "normalized_value": str(value.normalized_value) if value.normalized_value is not None else None,
                        "normalized_unit": value.normalized_unit,
                        "reporting_period_label": value.reporting_period_label,
                        "period_start_date": value.period_start_date.isoformat() if value.period_start_date else None,
                        "period_end_date": value.period_end_date.isoformat() if value.period_end_date else None,
                        "fiscal_year": value.fiscal_year,
                        "fiscal_quarter": value.fiscal_quarter,
                        "actuality": value.actuality,
                    }
                    for value in item.input_metrics
                ],
                "reporting_period_label": item.reporting_period_label,
                "currency_code": item.currency_code,
                "currency_symbol": item.currency_symbol,
                "period_start_date": item.period_start_date.isoformat() if item.period_start_date else None,
                "period_end_date": item.period_end_date.isoformat() if item.period_end_date else None,
            })
            if len(calculation_rows) >= _MAX_PROMPT_CALCULATIONS:
                break
        payload = {
            "sources": source_rows,
            "extracted_metrics": metric_rows,
            "calculations": calculation_rows,
            "missing_metrics": [key.value for key in extraction.missing_metrics],
            "unresolved_facts": [
                {
                    "metric_key": fact.metric_key.value if fact.metric_key else None,
                    "reason": fact.reason[:300],
                    "source_evidence_id": fact.source_evidence_id,
                    "excerpt": fact.supporting_excerpt[:320],
                }
                for fact in extraction.unresolved[:40]
            ],
            "unavailable_calculations": [
                {"calculation_key": item.calculation_key.value, "explanation": item.explanation}
                for item in calculations.unavailable
            ],
            "ambiguous_calculations": [
                {"calculation_key": item.calculation_key.value, "explanation": item.explanation}
                for item in calculations.ambiguous
            ],
        }
        def encode():
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
            return encoded

        encoded = encode()
        while len(encoded) > _MAX_PROMPT_CHARS:
            if calculation_rows:
                calculation_rows.pop()
            elif metric_rows:
                metric_rows.pop()
            elif payload["unresolved_facts"]:
                payload["unresolved_facts"].pop()
            elif payload["ambiguous_calculations"]:
                payload["ambiguous_calculations"].pop()
            elif payload["unavailable_calculations"]:
                payload["unavailable_calculations"].pop()
            elif source_rows:
                source_rows.pop()
            elif payload["missing_metrics"]:
                payload["missing_metrics"].pop()
            else:
                break
            encoded = encode()
        allowed_ids = {row["evidence_id"] for row in source_rows}
        metric_provenance: Dict[FinancialMetricKey, List[Any]] = {}
        for row in metric_rows:
            key = FinancialMetricKey(row["metric_key"])
            matching = [
                metric for metric in extraction.metrics
                if metric.metric_key == key
                and metric.source_evidence_id == row["source_evidence_id"]
                and metric.supporting_excerpt[:320] == row["supporting_excerpt"]
            ]
            metric_provenance.setdefault(key, []).extend(matching)
        calculation_provenance: Dict[CalculationKey, List[Any]] = {}
        for row in calculation_rows:
            key = CalculationKey(row["calculation_key"])
            matching = [
                calculation for calculation in calculations_all
                if calculation.calculation_key == key
                and calculation.status.value == row["status"]
                and calculation.source_evidence_ids == row["source_evidence_ids"]
                and calculation.reporting_period_label == row["reporting_period_label"]
            ]
            calculation_provenance.setdefault(key, []).extend(matching)
        prompt = (
            "Assess the startup's financial position across the eight required dimensions. "
            "Use only the supplied source excerpts and deterministic extracted metrics/calculations. "
            "Treat unavailable or ambiguous inputs as unknown; missing information alone is not a risk. "
            "Do not repeat or invent numeric figures, dates, URLs, source titles, or evidence IDs in prose. "
            "For each finding and concern, return exact supporting_evidence excerpts copied from source text "
            "and the matching evidence_ids. Overall claims must quote excerpts already attached to findings. "
            "Citations must support the relevant dimension and the cited metric/calculation provenance. "
            "For each claim, cite only supplied evidence_ids and metric/calculation keys. "
            "A dimension without relevant cited support must have risk_level UNKNOWN and empty references. "
            "Assess actual financial facts; distinguish reported figures from calculated ratios and forecasts. "
            "Return all eight dimensions exactly once, evidence-linked concerns, missing metric/calculation keys "
            "from the supplied unavailable lists, and practical investor next steps.\n\n"
            f"Grounding data: {encoded}"
        )
        return prompt, allowed_ids, metric_provenance, calculation_provenance

    def _validate_references(
        self,
        assessment: FinancialAssessmentResponse,
        evidence_ids: set[int],
        metric_provenance: Dict[FinancialMetricKey, List[Any]],
        calculation_provenance: Dict[CalculationKey, List[Any]],
        evidence_records: List[Any],
        missing_metric_keys: set[FinancialMetricKey],
        unavailable_calculation_keys: set[CalculationKey],
        ambiguous_calculation_keys: set[CalculationKey],
    ) -> None:
        evidence_by_id = {
            self._safe_int(self._evidence_value(record, "id")): record
            for record in evidence_records
            if self._safe_int(self._evidence_value(record, "id"))
        }
        for item in assessment.dimensions:
            self._validate_finding_support(
                item.dimension,
                [item.summary, item.explanation, item.investor_impact],
                evidence_ids=item.evidence_ids,
                supports=item.supporting_evidence,
                metric_keys=item.metric_keys,
                calculation_keys=item.calculation_keys,
                risk_level=item.risk_level,
                allowed_evidence_ids=evidence_ids,
                evidence_by_id=evidence_by_id,
                metric_provenance=metric_provenance,
                calculation_provenance=calculation_provenance,
            )
            if (item.metric_keys or item.calculation_keys) and not item.evidence_ids:
                raise ValueError("metric and calculation claims require source evidence IDs")
            if not item.evidence_ids and item.risk_level != RiskLevel.UNKNOWN:
                raise ValueError("a financial risk requires cited evidence")
        for concern in assessment.key_financial_concerns:
            self._validate_finding_support(
                concern.dimension,
                [concern.summary],
                evidence_ids=concern.evidence_ids,
                supports=concern.supporting_evidence,
                metric_keys=concern.metric_keys,
                calculation_keys=concern.calculation_keys,
                risk_level=None,
                allowed_evidence_ids=evidence_ids,
                evidence_by_id=evidence_by_id,
                metric_provenance=metric_provenance,
                calculation_provenance=calculation_provenance,
            )
        if not set(assessment.missing_information.metric_keys).issubset(missing_metric_keys):
            raise ValueError("assessment marked an available metric as missing")
        if not set(assessment.missing_information.unavailable_calculation_keys).issubset(unavailable_calculation_keys):
            raise ValueError("assessment marked an available calculation as unavailable")
        if not set(assessment.missing_information.ambiguous_calculation_keys).issubset(ambiguous_calculation_keys):
            raise ValueError("assessment marked a non-ambiguous calculation as ambiguous")
        dimension_supports = {
            (support.evidence_id, self._normalize_quote(support.excerpt))
            for item in assessment.dimensions
            for support in item.supporting_evidence
        }
        dimension_supports.update(
            (support.evidence_id, self._normalize_quote(support.excerpt))
            for item in assessment.key_financial_concerns
            for support in item.supporting_evidence
        )
        cited = {eid for item in assessment.dimensions for eid in item.evidence_ids}
        cited.update(eid for item in assessment.key_financial_concerns for eid in item.evidence_ids)
        for support in assessment.overall_supporting_evidence:
            if support.evidence_id not in cited:
                raise ValueError("overall claim cited evidence outside its findings")
            if (support.evidence_id, self._normalize_quote(support.excerpt)) not in dimension_supports:
                raise ValueError("overall claim excerpt is not attached to a cited finding")
            self._validate_exact_excerpt(support, evidence_by_id)
        overall_corpus = " ".join(support.excerpt for support in assessment.overall_supporting_evidence)
        overall_claim_terms = self._claim_tokens(
            assessment.overall_summary + " " + assessment.investor_impact
        ).intersection(_CLAIM_TERMS)
        if overall_claim_terms and not assessment.overall_supporting_evidence:
            raise ValueError("overall claims require excerpts from their supporting findings")
        self._validate_claim_text(assessment.overall_summary, overall_corpus)
        self._validate_claim_text(assessment.investor_impact, overall_corpus)
        for step in assessment.recommended_investor_next_steps:
            if self._contains_numeric_claim(step):
                raise ValueError("investor next step contains a numeric figure")
            domain_claims = self._claim_tokens(step).intersection(_CLAIM_TERMS)
            if not domain_claims.issubset(self._claim_tokens(overall_corpus)):
                raise ValueError("investor next step contains unsupported financial claims")
        risk_order = {
            RiskLevel.UNKNOWN: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        dimension_risks = [
            item.risk_level for item in assessment.dimensions
            if item.evidence_ids
        ]
        expected_overall_risk = max(dimension_risks, key=risk_order.get) if dimension_risks else RiskLevel.UNKNOWN
        if assessment.overall_risk != expected_overall_risk:
            raise ValueError("overall risk is inconsistent with the supported dimension findings")

    def _validate_finding_support(
        self,
        dimension: str,
        claims: List[str],
        evidence_ids: List[int],
        supports: List[EvidenceSupport],
        metric_keys: List[FinancialMetricKey],
        calculation_keys: List[CalculationKey],
        risk_level: Optional[RiskLevel],
        allowed_evidence_ids: set[int],
        evidence_by_id: Dict[int, Any],
        metric_provenance: Dict[FinancialMetricKey, List[Any]],
        calculation_provenance: Dict[CalculationKey, List[Any]],
    ) -> None:
        if not set(evidence_ids).issubset(allowed_evidence_ids):
            raise ValueError("claim cited evidence outside the current analysis or prompt")
        if set(support.evidence_id for support in supports) != set(evidence_ids):
            raise ValueError("each cited evidence ID requires an exact supporting excerpt")
        if not evidence_ids:
            if metric_keys or calculation_keys:
                raise ValueError("financial keys require cited source evidence")
            return

        if not set(metric_keys).issubset(_DIMENSION_METRICS[dimension]):
            raise ValueError("metric key does not belong to the cited financial dimension")
        if not set(calculation_keys).issubset(_DIMENSION_CALCULATIONS[dimension]):
            raise ValueError("calculation key does not belong to the cited financial dimension")

        linked_metric_records = []
        for key in metric_keys:
            candidates = [
                metric for metric in metric_provenance.get(key, [])
                if metric.source_evidence_id in evidence_ids
            ]
            if not candidates:
                raise ValueError("cited evidence does not match metric provenance")
            for metric in candidates:
                linked_metric_records.append(metric)
                if not any(
                    support.evidence_id == metric.source_evidence_id
                    and self._excerpt_matches_metric(support.excerpt, metric.supporting_excerpt)
                    for support in supports
                ):
                    raise ValueError("metric citation lacks its own supporting excerpt")

        linked_calculations = []
        for key in calculation_keys:
            candidates = calculation_provenance.get(key, [])
            candidates = [
                calculation for calculation in candidates
                if set(item.source_evidence_id for item in calculation.input_metrics).intersection(evidence_ids)
            ]
            if not candidates:
                raise ValueError("cited evidence does not match calculation input provenance")
            for calculation in candidates:
                linked_calculations.append(calculation)
                matching_inputs = [
                    metric for metric in calculation.input_metrics
                    if metric.source_evidence_id in evidence_ids
                ]
                if not any(
                    support.evidence_id == metric.source_evidence_id
                    and self._excerpt_matches_metric(support.excerpt, metric.supporting_excerpt)
                    for support in supports
                    for metric in matching_inputs
                ):
                    raise ValueError("calculation citation lacks an input metric excerpt")
                linked_metric_records.extend(matching_inputs)

        metric_text = " ".join(
            f"{metric.original_metric_label} {metric.metric_key.value} {metric.supporting_excerpt}"
            for metric in linked_metric_records
        )
        calculation_text = " ".join(
            f"{calculation.calculation_name} {calculation.calculation_key.value}"
            for calculation in linked_calculations
        )
        for support in supports:
            self._validate_exact_excerpt(support, evidence_by_id)
            is_key_backed = any(
                support.evidence_id == metric.source_evidence_id
                and self._excerpt_matches_metric(support.excerpt, metric.supporting_excerpt)
                for metric in linked_metric_records
            )
            if not is_key_backed and not self._excerpt_relevant_to_dimension(support.excerpt, dimension):
                raise ValueError("excerpt does not support the cited financial dimension")
        claim_corpus = " ".join(
            [support.excerpt for support in supports] + [metric_text, calculation_text]
        )
        for claim in claims:
            self._validate_claim_text(claim, claim_corpus)
        if risk_level is not None:
            if risk_level == RiskLevel.LOW and not self._has_unnegated_marker(claim_corpus, _STRENGTH_MARKERS):
                raise ValueError("low risk is not supported by a financial strength indicator")
            if risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}:
                if not self._has_unnegated_marker(claim_corpus, _RISK_MARKERS):
                    raise ValueError("risk level is not supported by a financial risk indicator")
            if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
                if not self._has_unnegated_marker(claim_corpus, _HIGH_RISK_MARKERS):
                    raise ValueError("high risk requires a directly supported adverse indicator")
            if risk_level == RiskLevel.CRITICAL and not self._has_unnegated_marker(claim_corpus, _CRITICAL_RISK_MARKERS):
                raise ValueError("critical risk requires a critical financial indicator")

    def _validate_exact_excerpt(
        self,
        support: EvidenceSupport,
        evidence_by_id: Dict[int, Any],
    ) -> None:
        source = evidence_by_id.get(support.evidence_id)
        if source is None:
            raise ValueError("supporting excerpt references unknown evidence")
        source_text = "\n".join(
            str(self._evidence_value(source, field) or "")
            for field in ("raw_text", "extracted_information")
        )
        if self._normalize_quote(support.excerpt) not in self._normalize_quote(source_text):
            raise ValueError("supporting excerpt is not present in stored evidence text")

    @staticmethod
    def _normalize_quote(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().casefold()

    def _excerpt_matches_metric(self, excerpt: str, metric_excerpt: str) -> bool:
        quote = self._normalize_quote(excerpt)
        metric_quote = self._normalize_quote(metric_excerpt)
        return bool(quote and metric_quote and (quote in metric_quote or metric_quote in quote))

    @staticmethod
    def _claim_tokens(text: str) -> set[str]:
        tokens = set(re.findall(r"[a-z]+", text.casefold())) - _CLAIM_STOPWORDS
        equivalents = {
            "liabilities": "liability", "expenses": "expense", "profits": "profit",
            "margins": "margin", "investors": "investor", "raised": "raise",
            "funded": "fund", "funding": "fund", "declined": "decline",
            "declining": "decline", "decreasing": "decrease", "decreased": "decrease",
            "increased": "increase", "increasing": "increase", "grew": "grow",
            "growing": "grow", "stronger": "strong", "weaker": "weak",
            "profitability": "profit", "profitable": "profit", "improved": "improve",
            "improving": "improve", "deteriorated": "deteriorate", "deteriorating": "deteriorate",
            "risks": "risk", "strengths": "strength",
        }
        return {equivalents.get(token, token) for token in tokens}

    def _validate_claim_text(self, claim: str, supporting_text: str) -> None:
        if not claim:
            return
        if self._contains_numeric_claim(claim):
            raise ValueError("claim contains an unsupported numeric figure")
        claim_terms = self._claim_tokens(claim)
        supporting_terms = self._claim_tokens(supporting_text)
        if not claim_terms.issubset(supporting_terms):
            raise ValueError("claim contains financial terms absent from its supporting evidence")
        if claim_terms and bool(_NEGATION.search(claim)) != bool(_NEGATION.search(supporting_text)):
            raise ValueError("claim polarity conflicts with its supporting evidence")

    @staticmethod
    def _contains_numeric_claim(text: str) -> bool:
        return bool(_NUMBER_TOKEN.search(text) or _NUMBER_WORD.search(text))

    @staticmethod
    def _has_unnegated_marker(text: str, markers: set[str]) -> bool:
        lowered = text.casefold()
        variants = {
            "decline": ("decline", "declined", "declining"),
            "loss": ("loss", "losses"),
            "default": ("default", "defaults", "defaulted", "defaulting"),
            "overdue": ("overdue", "past due"),
            "insolvent": ("insolvent", "insolvency"),
            "negative": ("negative", "negatively"),
            "deficit": ("deficit", "deficits"),
            "shortfall": ("shortfall", "shortfalls"),
            "weak": ("weak", "weaker", "weakest", "weakness"),
            "positive": ("positive", "positively"),
            "profit": ("profit", "profits", "profitable", "profitability"),
            "strong": ("strong", "stronger", "strength", "strengths"),
            "grow": ("grow", "grows", "grew", "growing", "growth"),
            "stable": ("stable", "stability"),
        }
        for marker in markers:
            options = variants.get(marker, (marker,))
            pattern = r"\b(?:" + "|".join(
                r"\s+".join(re.escape(part) for part in option.split())
                for option in options
            ) + r")\b"
            for match in re.finditer(pattern, lowered):
                preceding_text = lowered[max(0, match.start() - 60):match.start()]
                if not _NEGATION.search(preceding_text):
                    return True
        return False

    def _excerpt_relevant_to_dimension(self, excerpt: str, dimension: str) -> bool:
        excerpt_terms = self._claim_tokens(excerpt)
        dimension_terms = _DIMENSION_SUPPORT_TERMS[dimension]
        canonical_terms = {"liabilities": "liability", "funding": "fund", "raised": "raise"}
        dimension_terms = {canonical_terms.get(term, term) for term in dimension_terms}
        return bool(excerpt_terms.intersection(dimension_terms))

    def _assemble_output(
        self,
        analysis_id: int,
        evidence: List[Any],
        extraction: FinancialExtractionResult,
        calculations: FinancialCalculationResult,
        assessment: Optional[FinancialAssessmentResponse],
        llm_failure: Optional[str],
        pipeline_error: Optional[str],
    ) -> AgentOutput:
        by_id = {
            self._safe_int(self._evidence_value(item, "id")): item
            for item in evidence
            if self._safe_int(self._evidence_value(item, "id"))
        }
        details = {
            "Financial metrics and calculations": json.dumps(
                {
                    "extraction": extraction.model_dump(mode="json"),
                    "calculations": calculations.model_dump(mode="json"),
                },
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            ),
            "Limitations": self.CAVEAT,
        }
        findings: List[AgentFinding] = []
        references: Dict[int, EvidenceReference] = {}
        risk_levels: Dict[str, RiskLevel] = {}
        missing = [f"Financial metric unavailable: {key.value}." for key in extraction.missing_metrics]
        for fact in extraction.unresolved:
            missing.append(f"Unresolved {fact.metric_key.value if fact.metric_key else 'financial fact'}: {fact.reason}")
        for calculation in calculations.ambiguous + calculations.unavailable:
            missing.append(f"{calculation.calculation_name}: {calculation.explanation or calculation.status.value}.")
        if pipeline_error:
            missing.append(pipeline_error)
        if llm_failure:
            missing.append(llm_failure)
        if not evidence:
            missing.append("No financial or company evidence was available for this analysis.")

        assessment_by_name = {item.dimension: item for item in assessment.dimensions} if assessment else {}
        if assessment is None:
            retained_source_ids = {metric.source_evidence_id for metric in extraction.metrics}
            retained_source_ids.update(fact.source_evidence_id for fact in extraction.unresolved)
            for evidence_id in retained_source_ids:
                source = by_id.get(evidence_id)
                if source is not None:
                    references[evidence_id] = self._reference(
                        source,
                        self._best_snippet(self._evidence_text(source), ()),
                    )
        for dimension in _DIMENSIONS:
            item = assessment_by_name.get(dimension)
            if item is None:
                finding = AgentFinding(
                    dimension=dimension,
                    summary="No validated financial interpretation is available for this dimension.",
                    explanation="The extracted evidence and deterministic metrics are retained for review. No conclusion was inferred.",
                    risk_level=RiskLevel.UNKNOWN,
                    evidence_status=EvidenceStatus.UNAVAILABLE,
                    evidence_references=[],
                    investor_impact="Review the cited source material and request primary financial documentation.",
                )
            else:
                ids = list(item.evidence_ids)
                if not ids:
                    missing.append(f"{dimension}: no supporting source was cited.")
                statuses = [self._normalise_status(self._evidence_value(by_id[eid], "verification_status")) for eid in ids if eid in by_id]
                status = self._combine_status(statuses)
                for eid in ids:
                    if eid not in by_id:
                        continue
                    source = by_id[eid]
                    references.setdefault(eid, self._reference(source, self._best_snippet(self._evidence_text(source), ())))
                if ids:
                    finding = AgentFinding(
                        dimension=dimension,
                        summary=item.summary,
                        explanation=item.explanation,
                        risk_level=item.risk_level,
                        evidence_status=status,
                        evidence_references=ids,
                        investor_impact=item.investor_impact,
                    )
                else:
                    finding = AgentFinding(
                        dimension=dimension,
                        summary="No supporting financial evidence was cited for this dimension.",
                        explanation="No conclusion is made because the available evidence does not support a dimension-specific finding.",
                        risk_level=RiskLevel.UNKNOWN,
                        evidence_status=EvidenceStatus.UNAVAILABLE,
                        evidence_references=[],
                        investor_impact="Request primary financial records relevant to this dimension.",
                    )
            findings.append(finding)
            details[dimension] = finding.explanation
            risk_levels[dimension] = finding.risk_level

        # Keep concerns and next steps in the existing output details field.
        if assessment:
            details["Key financial concerns"] = json.dumps(
                [item.model_dump(mode="json") for item in assessment.key_financial_concerns],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            details["Recommended investor next steps"] = json.dumps(
                assessment.recommended_investor_next_steps,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            for concern in assessment.key_financial_concerns:
                for evidence_id in concern.evidence_ids:
                    source = by_id.get(evidence_id)
                    if source is not None:
                        references.setdefault(
                            evidence_id,
                            self._reference(source, self._best_snippet(self._evidence_text(source), ())),
                        )
            if references:
                details["Overall financial assessment"] = assessment.overall_summary
                risk_order = {
                    RiskLevel.UNKNOWN: 0,
                    RiskLevel.LOW: 1,
                    RiskLevel.MEDIUM: 2,
                    RiskLevel.HIGH: 3,
                    RiskLevel.CRITICAL: 4,
                }
                cited_risks = [finding.risk_level for finding in findings if finding.evidence_references]
                overall_risk = max(cited_risks, key=risk_order.get) if cited_risks else RiskLevel.UNKNOWN
                overall_summary = assessment.overall_summary
            else:
                details["Overall financial assessment"] = "No supported financial conclusion is available from the supplied evidence."
                overall_risk = RiskLevel.UNKNOWN
                overall_summary = "No supported financial conclusion is available from the supplied evidence."
        else:
            overall_risk = RiskLevel.UNKNOWN
            overall_summary = "LLM interpretation is unavailable; deterministic financial extraction and calculations are retained."
        cited_statuses = [references[eid].verification_status for eid in references]
        overall_status = self._combine_status(cited_statuses)
        if overall_status != EvidenceStatus.VERIFIED:
            missing.append("Independent verification of cited public sources has not been completed.")
        return AgentOutput(
            agent_name=self.name,
            analysis_id=analysis_id,
            findings=findings,
            detailed_explanations=details,
            evidence_references=list(references.values()),
            risk_level=overall_risk,
            risk_levels=risk_levels,
            evidence_status=overall_status,
            investor_impact=(assessment.investor_impact if assessment and references else overall_summary),
            missing_information=list(dict.fromkeys(missing)),
            execution_status=(ExecutionStatus.PARTIAL if missing or llm_failure or pipeline_error else ExecutionStatus.SUCCESS),
            error_details=None,
        )

    @staticmethod
    def _combine_status(statuses: List[EvidenceStatus]) -> EvidenceStatus:
        if not statuses:
            return EvidenceStatus.UNAVAILABLE
        if EvidenceStatus.UNVERIFIED in statuses:
            return EvidenceStatus.UNVERIFIED
        if EvidenceStatus.PARTIALLY_VERIFIED in statuses:
            return EvidenceStatus.PARTIALLY_VERIFIED
        return EvidenceStatus.VERIFIED
