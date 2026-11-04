import json
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from pydantic import ValidationError

from app.agents.financial import (
    EvidenceSupport,
    FinancialAgent,
    FinancialAssessmentResponse,
    _DIMENSIONS,
)
from app.agents.output import AgentOutput, EvidenceStatus, ExecutionStatus, RiskLevel
from app.financial import (
    CalculationKey,
    FinancialCalculationResult,
    FinancialExtractionResult,
    FinancialMetric,
    FinancialMetricKey,
    StatementType,
    extract_financials,
)
from app.llm.gateway import LLMResponse


def _assessment(evidence_id=1, excerpt="Revenue declined to USD 120 million in FY2024."):
    dimensions = []
    for name in _DIMENSIONS:
        is_revenue = name == "Revenue"
        dimensions.append({
            "dimension": name,
            "summary": "Reported revenue is available for assessment." if is_revenue else "No supported conclusion is available.",
            "explanation": "The cited source reports a financial statement item." if is_revenue else "No relevant source was supplied.",
            "risk_level": "MEDIUM" if is_revenue else "UNKNOWN",
            "evidence_ids": [evidence_id] if is_revenue else [],
            "supporting_evidence": [{"evidence_id": evidence_id, "excerpt": excerpt}] if is_revenue else [],
            "metric_keys": ["revenue"] if is_revenue else [],
            "calculation_keys": [],
            "investor_impact": "Review the reported financial information." if is_revenue else "Request primary financial records.",
        })
    return FinancialAssessmentResponse.model_validate({
        "overall_summary": "The reported revenue is available for review.",
        "overall_risk": "MEDIUM",
        "investor_impact": "Review the available source material.",
        "key_financial_concerns": [{
            "summary": "Review the cited revenue source.",
            "dimension": "Revenue",
            "evidence_ids": [evidence_id],
            "supporting_evidence": [{"evidence_id": evidence_id, "excerpt": excerpt}],
            "metric_keys": ["revenue"],
            "calculation_keys": [],
        }],
        "overall_supporting_evidence": [{"evidence_id": evidence_id, "excerpt": excerpt}],
        "recommended_investor_next_steps": ["Request primary financial statements."],
        "dimensions": dimensions,
    })


class StubGateway:
    def __init__(self, assessment=None, error=None, provider="Test Provider"):
        self.assessment = assessment
        self.error = error
        self.provider = provider
        self.prompt = None

    async def generate(self, *, prompt, agent_name, response_schema):
        self.prompt = prompt
        assert response_schema is FinancialAssessmentResponse
        if self.error:
            raise self.error
        return LLMResponse(provider=self.provider, model="test", text="{}", parsed=self.assessment)


class FinancialAgentIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def evidence(self, **overrides):
        item = {
            "id": 1,
            "analysis_id": 10,
            "startup_id": 5,
            "source_url": "https://example.test/annual-report",
            "source_title": "Annual report",
            "source_category": "financial",
            "extracted_information": "Revenue declined to USD 120 million in FY2024.",
            "raw_text": "Revenue declined to USD 120 million in FY2024.",
            "verification_status": "verified",
            "source_metadata": {},
        }
        item.update(overrides)
        return item

    async def test_runs_extraction_calculation_and_llm_assessment(self):
        gateway = StubGateway(assessment=_assessment())
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )

        self.assertIsInstance(output, AgentOutput)
        self.assertEqual(output.execution_status, ExecutionStatus.PARTIAL)
        self.assertEqual(len(output.findings), 8)
        revenue = next(item for item in output.findings if item.dimension == "Revenue")
        self.assertEqual(revenue.risk_level, RiskLevel.MEDIUM)
        self.assertEqual(revenue.evidence_references, [1])
        self.assertEqual(output.evidence_references[0].source_url, "https://example.test/annual-report")
        self.assertEqual(revenue.evidence_status, EvidenceStatus.VERIFIED)
        data = json.loads(output.detailed_explanations["Financial metrics and calculations"])
        self.assertEqual(data["extraction"]["metrics"][0]["metric_key"], "revenue")
        self.assertIn("annual_revenue_growth", {row["calculation_key"] for row in data["calculations"]["unavailable"]})
        self.assertIn('"evidence_id":1', gateway.prompt)
        self.assertIn('"extracted_metrics"', gateway.prompt)
        self.assertIn('"calculations"', gateway.prompt)
        self.assertIn("cited revenue source", output.detailed_explanations["Key financial concerns"])
        self.assertIn("primary financial statements", output.detailed_explanations["Recommended investor next steps"])

    async def test_provider_failure_returns_unknown_dimensions_and_keeps_metrics(self):
        gateway = StubGateway(error=RuntimeError("provider secret details"))
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.execution_status, ExecutionStatus.PARTIAL)
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertTrue(all(item.risk_level == RiskLevel.UNKNOWN for item in output.findings))
        self.assertTrue(any(item.startswith("LLM interpretation was unavailable") for item in output.missing_information))
        self.assertIn('"metric_key":"revenue"', output.detailed_explanations["Financial metrics and calculations"])
        self.assertNotIn("provider secret details", output.missing_information)

    async def test_rejects_cross_analysis_evidence_ids(self):
        gateway = StubGateway(assessment=_assessment(evidence_id=999))
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertEqual([item.evidence_id for item in output.evidence_references], [1])
        self.assertTrue(any("did not pass validation" in item for item in output.missing_information))

    async def test_excludes_evidence_from_other_analyses(self):
        gateway = StubGateway(assessment=_assessment())
        output = await FinancialAgent(gateway=gateway).run(
            5,
            {"analysis_id": 10, "evidence": [self.evidence(analysis_id=11)]},
        )
        self.assertEqual(output.evidence_references, [])
        self.assertNotIn("annual-report", gateway.prompt)
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)

    async def test_numeric_claims_from_llm_are_rejected(self):
        assessment = _assessment().model_copy(deep=True)
        revenue = next(item for item in assessment.dimensions if item.dimension == "Revenue")
        revenue.summary = "Revenue increased to 999."
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertEqual([item.evidence_id for item in output.evidence_references], [1])

    async def test_unknown_metric_key_is_rejected(self):
        assessment = _assessment().model_copy(deep=True)
        revenue = next(item for item in assessment.dimensions if item.dimension == "Revenue")
        revenue.metric_keys = [FinancialMetricKey.NET_INCOME]
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertTrue(any("did not pass validation" in item for item in output.missing_information))

    async def test_revenue_source_cannot_support_a_debt_finding(self):
        assessment = _assessment().model_copy(deep=True)
        debt = next(item for item in assessment.dimensions if item.dimension == "Debt and liabilities")
        debt.summary = "The company has outstanding debt."
        debt.explanation = "The source confirms that debt is outstanding."
        debt.investor_impact = "Debt could affect the financial position."
        debt.risk_level = RiskLevel.HIGH
        debt.evidence_ids = [1]
        debt.supporting_evidence = [
            EvidenceSupport(evidence_id=1, excerpt="Revenue declined to USD 120 million in FY2024.")
        ]
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertTrue(all(item.risk_level == RiskLevel.UNKNOWN for item in output.findings))

    async def test_metric_from_wrong_dimension_is_rejected(self):
        debt_evidence = self.evidence(
            id=2,
            source_title="Debt note",
            source_url="https://example.test/debt-note",
            extracted_information="Outstanding debt includes a term loan.",
            raw_text="Outstanding debt includes a term loan.",
        )
        assessment = _assessment().model_copy(deep=True)
        debt = next(item for item in assessment.dimensions if item.dimension == "Debt and liabilities")
        debt.summary = "Debt obligations are disclosed."
        debt.explanation = "The source discusses debt obligations."
        debt.investor_impact = "Review the debt disclosure."
        debt.evidence_ids = [2]
        debt.supporting_evidence = [
            EvidenceSupport(evidence_id=2, excerpt="Outstanding debt includes a term loan.")
        ]
        debt.metric_keys = [FinancialMetricKey.REVENUE]
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence(), debt_evidence]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertTrue(any("did not pass validation" in item for item in output.missing_information))

    async def test_metric_id_must_match_metric_source_provenance(self):
        unrelated = self.evidence(
            id=2,
            source_title="Operations note",
            source_url="https://example.test/operations-note",
            extracted_information="The operations team reports routine activity.",
            raw_text="The operations team reports routine activity.",
        )
        assessment = _assessment().model_copy(deep=True)
        revenue = next(item for item in assessment.dimensions if item.dimension == "Revenue")
        revenue.evidence_ids = [2]
        revenue.supporting_evidence = [
            EvidenceSupport(evidence_id=2, excerpt="The operations team reports routine activity.")
        ]
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence(), unrelated]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)

    async def test_calculation_citation_must_match_input_metric_provenance(self):
        statement = "Revenue was USD 120 million in FY2024. Net income was USD 12 million in FY2024."
        source = self.evidence(extracted_information=statement, raw_text=statement)
        unrelated = self.evidence(
            id=2,
            source_title="Profitability note",
            source_url="https://example.test/profitability-note",
            extracted_information="Profitability review discusses business operations.",
            raw_text="Profitability review discusses business operations.",
        )
        assessment = _assessment().model_copy(deep=True)
        profit = next(item for item in assessment.dimensions if item.dimension == "Profitability")
        profit.summary = "The net profit margin is available."
        profit.explanation = "The profit margin is assessed from reported statements."
        profit.investor_impact = "Review the profit margin calculation."
        profit.evidence_ids = [2]
        profit.supporting_evidence = [
            EvidenceSupport(evidence_id=2, excerpt="Profitability review discusses business operations.")
        ]
        profit.metric_keys = []
        profit.calculation_keys = [CalculationKey.NET_PROFIT_MARGIN]
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [source, unrelated]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)

    async def test_calculation_with_matching_input_provenance_is_accepted(self):
        statement = "Revenue declined to USD 120 million in FY2024. Net income was USD 12 million in FY2024."
        source = self.evidence(extracted_information=statement, raw_text=statement)
        assessment = _assessment(excerpt="Revenue declined to USD 120 million in FY2024.").model_copy(deep=True)
        profit = next(item for item in assessment.dimensions if item.dimension == "Profitability")
        profit.summary = "The net profit margin is available."
        profit.explanation = "The calculation uses reported revenue and net income."
        profit.investor_impact = "Review the net profit margin."
        profit.evidence_ids = [1]
        profit.supporting_evidence = [
            EvidenceSupport(evidence_id=1, excerpt="Revenue declined to USD 120 million in FY2024."),
            EvidenceSupport(evidence_id=1, excerpt="Net income was USD 12 million in FY2024."),
        ]
        profit.metric_keys = []
        profit.calculation_keys = [CalculationKey.NET_PROFIT_MARGIN]
        assessment = FinancialAssessmentResponse.model_validate(assessment.model_dump(mode="python"))
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [source]}
        )
        finding = next(item for item in output.findings if item.dimension == "Profitability")
        self.assertEqual(finding.summary, "The net profit margin is available.")
        self.assertEqual(finding.risk_level, RiskLevel.UNKNOWN)

    async def test_unsupported_overall_summary_and_investor_impact_are_rejected(self):
        for field, claim in (
            ("overall_summary", "Revenue grew strongly."),
            ("investor_impact", "Revenue distress requires immediate debt restructuring."),
        ):
            assessment = _assessment().model_copy(deep=True)
            setattr(assessment, field, claim)
            gateway = StubGateway(assessment=assessment)
            output = await FinancialAgent(gateway=gateway).run(
                5, {"analysis_id": 10, "evidence": [self.evidence()]}
            )
            self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
            self.assertTrue(all(item.risk_level == RiskLevel.UNKNOWN for item in output.findings))

    async def test_invented_supporting_excerpt_is_rejected(self):
        assessment = _assessment().model_copy(deep=True)
        revenue = next(item for item in assessment.dimensions if item.dimension == "Revenue")
        revenue.supporting_evidence = [
            EvidenceSupport(evidence_id=1, excerpt="Revenue increased strongly in every quarter.")
        ]
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertTrue(all(item.risk_level == RiskLevel.UNKNOWN for item in output.findings))

    async def test_invalid_risk_level_is_rejected_by_response_schema(self):
        value = _assessment().model_dump(mode="python")
        value["dimensions"][0]["risk_level"] = "EXTREME"
        with self.assertRaises(ValidationError):
            FinancialAssessmentResponse.model_validate(value)

    async def test_llm_cannot_upgrade_evidence_verification_status(self):
        gateway = StubGateway(assessment=_assessment())
        output = await FinancialAgent(gateway=gateway).run(
            5,
            {"analysis_id": 10, "evidence": [self.evidence(verification_status="unverified")]},
        )
        revenue = next(item for item in output.findings if item.dimension == "Revenue")
        self.assertEqual(revenue.evidence_status, EvidenceStatus.UNVERIFIED)
        self.assertEqual(output.evidence_references[0].verification_status, EvidenceStatus.UNVERIFIED)

    async def test_forecast_status_is_preserved_in_extraction_and_prompt(self):
        text = "Forecast revenue declined to USD 120 million in FY2024."
        gateway = StubGateway(assessment=_assessment(excerpt=text))
        output = await FinancialAgent(gateway=gateway).run(
            5,
            {"analysis_id": 10, "evidence": [self.evidence(raw_text=text, extracted_information=text)]},
        )
        data = json.loads(output.detailed_explanations["Financial metrics and calculations"])
        revenue = next(metric for metric in data["extraction"]["metrics"] if metric["metric_key"] == "revenue")
        self.assertEqual(revenue["actuality"], "forecast_or_target")
        self.assertIn('"actuality":"forecast_or_target"', gateway.prompt)

    async def test_prompt_preserves_complete_metric_period_unit_and_statement_context(self):
        evidence = self.evidence(raw_text="Revenue was reported for this interval.", extracted_information="Revenue was reported for this interval.")
        metric = FinancialMetric(
            metric_key=FinancialMetricKey.REVENUE,
            original_metric_label="Revenue",
            normalized_value=Decimal("120000000"),
            original_numeric_value="USD 120 million",
            currency_code="USD",
            normalized_unit="currency_amount",
            original_unit_scale="million",
            reporting_period_label="FY2024",
            period_start_date=date(2023, 7, 1),
            period_end_date=date(2024, 6, 30),
            fiscal_year=2024,
            fiscal_quarter=None,
            statement_type=StatementType.INCOME_STATEMENT,
            source_evidence_id=1,
            source_url=evidence["source_url"],
            source_title=evidence["source_title"],
            source_category="financial",
            supporting_excerpt="Revenue was reported for this interval.",
            evidence_verification_status="verified",
            actuality="forecast_or_target",
        )
        agent = FinancialAgent(gateway=StubGateway())
        prompt, _, _, _ = agent._build_prompt(
            [evidence],
            FinancialExtractionResult(metrics=[metric], missing_metrics=[]),
            FinancialCalculationResult(),
        )
        payload = json.loads(prompt.split("Grounding data: ", 1)[1])
        item = payload["extracted_metrics"][0]
        self.assertEqual(item["period_start_date"], "2023-07-01")
        self.assertEqual(item["period_end_date"], "2024-06-30")
        self.assertEqual(item["normalized_unit"], "currency_amount")
        self.assertEqual(item["statement_type"], "income_statement")
        self.assertEqual(item["actuality"], "forecast_or_target")
        self.assertEqual(item["source_evidence_id"], 1)

    async def test_successful_analysis_keeps_caveat_out_of_missing_information(self):
        source_texts = {
            "Funding history": "The company completed a seed funding round.",
            "Revenue": "Revenue declined to USD 120 million in FY2024.",
            "Profitability": "The filing discusses profit margins.",
            "Cash flow": "The report discusses cash flow and operating burn.",
            "Liquidity": "The filing discusses liquidity and working capital.",
            "Debt and liabilities": "The note discusses outstanding debt and liabilities.",
            "Financial strengths": "The report identifies financial strengths in positive cash flow.",
            "Financial risks": "The report identifies liquidity risk and debt exposure.",
        }
        evidence = [
            self.evidence(
                id=index,
                source_title=f"Source {index}",
                source_url=f"https://example.test/source-{index}",
                raw_text=text,
                extracted_information=text,
            )
            for index, text in enumerate(source_texts.values(), start=1)
        ]
        assessment = _assessment(evidence_id=2, excerpt=source_texts["Revenue"]).model_copy(deep=True)
        for index, (dimension, excerpt) in enumerate(source_texts.items(), start=1):
            if dimension == "Revenue":
                continue
            item = next(value for value in assessment.dimensions if value.dimension == dimension)
            item.summary = f"{dimension} information is available."
            item.explanation = f"The cited source discusses {dimension.lower()}."
            item.investor_impact = "Review the cited source."
            item.evidence_ids = [index]
            item.supporting_evidence = [EvidenceSupport(evidence_id=index, excerpt=excerpt)]
            item.risk_level = RiskLevel.UNKNOWN
        assessment = FinancialAssessmentResponse.model_validate(assessment.model_dump(mode="python"))
        gateway = StubGateway(assessment=assessment)
        agent = FinancialAgent(gateway=gateway)
        extracted = extract_financials([evidence[1]])
        extracted.missing_metrics = []
        with patch.object(agent, "_extract_and_calculate", return_value=(extracted, FinancialCalculationResult(), None)):
            output = await agent.run(5, {"analysis_id": 10, "evidence": evidence})
        self.assertEqual(output.execution_status, ExecutionStatus.SUCCESS, output.missing_information)
        self.assertFalse(any("not audited" in item for item in output.missing_information))
        self.assertIn("not audited", output.detailed_explanations["Limitations"])

    async def test_mock_provider_fallback_preserves_metrics_and_references(self):
        gateway = StubGateway(assessment=_assessment(), provider="Mock LLM")
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.execution_status, ExecutionStatus.PARTIAL)
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertEqual([item.evidence_id for item in output.evidence_references], [1])
        self.assertIn('"metric_key":"revenue"', output.detailed_explanations["Financial metrics and calculations"])

    async def test_non_unknown_overall_risk_requires_cited_evidence(self):
        assessment = _assessment().model_copy(deep=True)
        assessment.dimensions = [item.model_copy(update={"evidence_ids": [], "metric_keys": [], "risk_level": RiskLevel.UNKNOWN}) for item in assessment.dimensions]
        assessment.overall_risk = RiskLevel.CRITICAL
        # Validation is enforced by the agent in addition to the response model.
        gateway = StubGateway(assessment=assessment)
        output = await FinancialAgent(gateway=gateway).run(
            5, {"analysis_id": 10, "evidence": [self.evidence()]}
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertEqual([item.evidence_id for item in output.evidence_references], [1])


if __name__ == "__main__":
    unittest.main()
