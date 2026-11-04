
"""Agent tests using clearly labelled demonstration data only.

Every evidence record below is fictional and marked "[DEMO]".
The example domain is reserved for documentation.
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import (
    AgentOutput,
    EvidenceStatus,
    ExecutionStatus,
    FinancialAgent,
    LegalAgent,
    MarketingAgent,
    RiskLevel,
)
from app.db.models import Analysis, Evidence, Startup
from app.db.session import Base


class AgentTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.startup = Startup(
            name="DemoCo",
            website="https://demo.ventrix.example",
            industry="Workflow software",
        )
        self.db.add(self.startup)
        self.db.flush()

        self.analysis = Analysis(
            startup_name="DemoCo",
            website="https://demo.ventrix.example",
            industry="Workflow software",
            status="pending",
        )
        self.db.add(self.analysis)
        self.db.commit()
        self.db.refresh(self.startup)
        self.db.refresh(self.analysis)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_evidence(
        self,
        *,
        title,
        category,
        text,
        status="unverified",
        related_agent="company_research_agent",
    ):
        evidence = Evidence(
            startup_id=self.startup.id,
            analysis_id=self.analysis.id,
            source_url=(
                "https://demo.ventrix.example/"
                f"{title.lower().replace(' ', '-')}"
            ),
            source_title=f"[DEMO] {title}",
            source_category=category,
            extracted_information=f"DEMO DATA ONLY. {text}",
            raw_text=f"DEMO DATA ONLY. {text}",
            verification_status=status,
            related_agent=related_agent,
            findings=[],
            source_metadata={"demonstration_data": True},
            content_hash=f"demo-{title.lower().replace(' ', '-')}",
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def financial_demo_evidence(self):
        return [
            self.add_evidence(
                title="Seed announcement",
                category="financial",
                text=(
                    "DemoCo raised a $1.5 million seed round led by Demo "
                    "Ventures in 2025. The company reported annual recurring "
                    "revenue of $2.4 million."
                ),
                status="verified",
                related_agent="financial_analysis_agent",
            ),
            self.add_evidence(
                title="Financial snapshot",
                category="financial",
                text=(
                    "DemoCo is not yet profitable and reported an operating "
                    "loss. Monthly cash burn is $120,000 with runway of 14 "
                    "months. The company has no outstanding debt."
                ),
                status="partially_verified",
                related_agent="financial_analysis_agent",
            ),
        ]

    def marketing_demo_evidence(self):
        return [
            self.add_evidence(
                title="Market brief",
                category="marketing",
                text=(
                    "The workflow automation industry has a growing market "
                    "size and is forecast to grow at a 12% CAGR. Demand is "
                    "strongest among mid-sized finance teams."
                ),
                status="verified",
                related_agent="market_analysis_agent",
            ),
            self.add_evidence(
                title="Competitive landscape",
                category="marketing",
                text=(
                    "DemoCo competes with larger incumbents in a highly "
                    "competitive market with intense competition and pricing "
                    "pressure. DemoCo positions itself as a specialist and "
                    "differentiates through a proprietary finance workflow "
                    "integration."
                ),
                status="partially_verified",
                related_agent="market_analysis_agent",
            ),
            self.add_evidence(
                title="Customer story",
                category="marketing",
                text=(
                    "DemoCo targets mid-market finance teams and reports "
                    "growth opportunities through partner channels."
                ),
                status="unverified",
                related_agent="market_analysis_agent",
            ),
        ]

    def legal_demo_evidence(self):
        return [
            self.add_evidence(
                title="Registry extract",
                category="legal",
                text=(
                    "DemoCo is registered in Delaware under company number "
                    "1234567. The registered office is in Wilmington."
                ),
                status="verified",
                related_agent="legal_compliance_agent",
            ),
            self.add_evidence(
                title="Privacy notice",
                category="legal",
                text=(
                    "DemoCo publishes a privacy notice describing GDPR and "
                    "data protection practices."
                ),
                status="partially_verified",
                related_agent="legal_compliance_agent",
            ),
            self.add_evidence(
                title="Trademark record",
                category="legal",
                text=(
                    "DemoCo has a pending trademark application for its "
                    "product name."
                ),
                status="unverified",
                related_agent="legal_compliance_agent",
            ),
        ]

    def finding(self, output, dimension):
        return next(
            item for item in output.findings
            if item.dimension == dimension
        )



class FinancialAgentTests(AgentTestCase):

    async def test_financial_agent_preserves_deterministic_financial_data_without_llm(self):
        evidence = self.financial_demo_evidence()
        agent = FinancialAgent(self.db)

        output = await agent.execute(
            self.startup.id,
            {"analysis_id": self.analysis.id},
        )

        self.assertIsInstance(output, AgentOutput)
        self.assertEqual(output.agent_name, "Financial Agent")
        self.assertEqual(output.analysis_id, self.analysis.id)
        self.assertEqual(output.execution_status, ExecutionStatus.PARTIAL)
        self.assertEqual(len(output.findings), 8)
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)
        self.assertTrue(
            all(item.risk_level == RiskLevel.UNKNOWN for item in output.findings)
        )
        self.assertTrue(
            any(
                item.startswith("LLM interpretation was unavailable")
                for item in output.missing_information
            )
        )
        self.assertIn(
            "Financial metrics and calculations",
            output.detailed_explanations,
        )
        self.assertTrue(evidence)



class MarketingAgentTests(AgentTestCase):

    def get_spec(self, dimension):
        agent = MarketingAgent(self.db)
        return next(
            spec for spec in agent.DIMENSION_SPECS
            if spec.name == dimension
        )

    async def test_marketing_agent_uses_demo_market_evidence(self):
        self.marketing_demo_evidence()
        agent = MarketingAgent(self.db)

        output = await agent.execute(
            self.startup.id,
            {"analysis_id": self.analysis.id},
        )

        self.assertEqual(output.agent_name, "Marketing Agent")
        self.assertEqual(output.execution_status, ExecutionStatus.PARTIAL)
        self.assertEqual(
            output.evidence_status,
            EvidenceStatus.PARTIALLY_VERIFIED,
        )
        self.assertEqual(output.risk_level, RiskLevel.HIGH)

        customers = self.finding(output, "Target customers")
        self.assertIn("finance teams", customers.summary)
        self.assertEqual(
            customers.evidence_status,
            EvidenceStatus.VERIFIED,
        )

        competitors = self.finding(output, "Competitor analysis")
        self.assertEqual(competitors.risk_level, RiskLevel.HIGH)
        self.assertIn("intense competition", competitors.explanation)

        differentiation = self.finding(
            output,
            "Competitive differentiation",
        )
        self.assertIn("proprietary", differentiation.explanation)

        self.assertIn(
            "market size",
            output.detailed_explanations["Industry overview"].lower(),
        )

    def test_matching_rejects_accidental_substring(self):
        evidence = self.add_evidence(
            title="General research",
            category="marketing",
            text="The company is enterprising and innovative.",
        )

        agent = MarketingAgent(self.db)
        matches = agent._match_dimension(
            self.get_spec("Target customers"),
            [evidence],
        )

        self.assertEqual(matches, [])

    def test_matching_accepts_complete_keyword(self):
        evidence = self.add_evidence(
            title="Enterprise customers",
            category="marketing",
            text="The company serves enterprise customers.",
        )

        agent = MarketingAgent(self.db)
        matches = agent._match_dimension(
            self.get_spec("Target customers"),
            [evidence],
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].evidence.id, evidence.id)

    def test_matching_accepts_complete_phrase(self):
        evidence = self.add_evidence(
            title="Pricing research",
            category="marketing",
            text="The competitor uses a flexible pricing model.",
        )

        agent = MarketingAgent(self.db)
        matches = agent._match_dimension(
            self.get_spec("Competitor analysis"),
            [evidence],
        )

        self.assertEqual(len(matches), 1)
        self.assertIn("pricing model", matches[0].snippet.lower())

    def test_matching_supports_singular_and_plural_customer_keywords(self):
        singular = self.add_evidence(
            title="Customer profile",
            category="marketing",
            text="The ideal customer is a finance manager.",
        )

        plural = self.add_evidence(
            title="Customers research",
            category="marketing",
            text="The company serves customers across multiple industries.",
        )

        agent = MarketingAgent(self.db)
        matches = agent._match_dimension(
            self.get_spec("Target customers"),
            [singular, plural],
        )

        matched_ids = {
            match.evidence.id for match in matches
        }

        self.assertIn(singular.id, matched_ids)
        self.assertIn(plural.id, matched_ids)

    def test_matching_ranks_preferred_category_and_title_higher(self):
        preferred = self.add_evidence(
            title="Market overview",
            category="marketing",
            text="The industry has several established players.",
        )

        non_preferred = self.add_evidence(
            title="General report",
            category="company",
            text="The industry has several established players.",
        )

        agent = MarketingAgent(self.db)
        matches = agent._match_dimension(
            self.get_spec("Industry overview"),
            [non_preferred, preferred],
        )

        self.assertEqual(matches[0].evidence.id, preferred.id)
        self.assertGreater(matches[0].score, matches[1].score)

    def test_matching_returns_at_most_five_evidence_sources(self):
        evidence = [
            self.add_evidence(
                title=f"Market report {index}",
                category="marketing",
                text="The industry has a growing market and demand.",
            )
            for index in range(7)
        ]

        agent = MarketingAgent(self.db)
        matches = agent._match_dimension(
            self.get_spec("Market trends"),
            evidence,
        )

        self.assertEqual(len(matches), 5)



    async def test_marketing_agent_matches_expanded_market_intelligence_keywords(self):
        evidence_items = [
            (
                "Technology adoption trend",
                "The industry is seeing rapid technology adoption and digital "
                "transformation, creating a changing market outlook.",
                "Market trends",
            ),
            (
                "Buyer persona research",
                "The ideal customer profile and buyer persona are mid-sized "
                "business finance teams with specific customer needs.",
                "Target customers",
            ),
            (
                "Competitor landscape update",
                "A direct competitor and several market leaders compete through "
                "different pricing models. The market also faces pricing pressure.",
                "Competitor analysis",
            ),
            (
                "Expansion strategy",
                "Growth opportunities include geographic expansion, strategic "
                "partnerships and new distribution channels.",
                "Growth opportunities",
            ),
            (
                "Market risk outlook",
                "The business faces market volatility, economic downturn risk "
                "and changing regulations.",
                "Market risks",
            ),
        ]

        created_evidence = {}
        for title, text, dimension in evidence_items:
            created_evidence[dimension] = self.add_evidence(
                title=title,
                category="marketing",
                text=text,
                status="verified",
                related_agent="market_analysis_agent",
            )

        agent = MarketingAgent(self.db)
        output = await agent.execute(
            self.startup.id,
            {"analysis_id": self.analysis.id},
        )

        for dimension, evidence in created_evidence.items():
            with self.subTest(dimension=dimension):
                finding = self.finding(output, dimension)
                self.assertIn(evidence.id, finding.evidence_references)
                self.assertNotEqual(
                    finding.evidence_status,
                    EvidenceStatus.UNAVAILABLE,
                    f"{dimension} should match its supporting demo evidence",
                )


class LegalAgentTests(AgentTestCase):

    async def test_legal_agent_reports_evidence_without_claiming_compliance(self):
        self.legal_demo_evidence()
        agent = LegalAgent(self.db)

        output = await agent.execute(
            self.startup.id,
            {"analysis_id": self.analysis.id},
        )

        self.assertEqual(output.agent_name, "Legal Agent")

        registration = self.finding(
            output,
            "Company registration information",
        )
        self.assertEqual(
            registration.evidence_status,
            EvidenceStatus.VERIFIED,
        )
        self.assertIn("company number 1234567", registration.summary)

        compliance = self.finding(output, "Compliance concerns")
        self.assertEqual(
            compliance.evidence_status,
            EvidenceStatus.PARTIALLY_VERIFIED,
        )
        self.assertIn("privacy notice", compliance.explanation)

        ip = self.finding(
            output,
            "Potential intellectual property concerns",
        )
        self.assertEqual(
            ip.evidence_status,
            EvidenceStatus.UNVERIFIED,
        )

        serialised = output.model_dump_json().lower()
        self.assertNotIn("legally compliant", serialised)
        self.assertNotIn("is compliant", serialised)

        self.assertTrue(
            any(
                item.startswith("Available legal records:")
                for item in output.missing_information
            )
        )

        self.assertEqual(
            output.evidence_status,
            EvidenceStatus.PARTIALLY_VERIFIED,
        )

    async def test_legal_agent_returns_unknown_when_no_legal_evidence(self):
        agent = LegalAgent(self.db)

        output = await agent.execute(
            self.startup.id,
            {"analysis_id": self.analysis.id},
        )

        self.assertEqual(
            output.evidence_status,
            EvidenceStatus.UNAVAILABLE,
        )
        self.assertEqual(output.risk_level, RiskLevel.UNKNOWN)

        registration = self.finding(
            output,
            "Company registration information",
        )
        self.assertEqual(registration.risk_level, RiskLevel.UNKNOWN)

        self.assertIn(
            "Company registration information: no supporting evidence was found.",
            output.missing_information,
        )


class AgentExecutionTests(AgentTestCase):

    async def test_missing_analysis_id_returns_structured_failure(self):
        agent = LegalAgent(self.db)

        output = await agent.execute(self.startup.id, {})

        self.assertIsInstance(output, AgentOutput)
        self.assertEqual(output.execution_status, ExecutionStatus.FAILED)
        self.assertEqual(output.analysis_id, 0)
        self.assertIn("analysis_id is required", output.error_details)
        self.assertEqual(
            output.evidence_status,
            EvidenceStatus.UNAVAILABLE,
        )

    async def test_agents_work_independently(self):
        self.financial_demo_evidence()
        self.marketing_demo_evidence()
        self.legal_demo_evidence()

        context = {"analysis_id": self.analysis.id}

        financial = await FinancialAgent(self.db).execute(
            self.startup.id,
            context,
        )
        marketing = await MarketingAgent(self.db).execute(
            self.startup.id,
            context,
        )
        legal = await LegalAgent(self.db).execute(
            self.startup.id,
            context,
        )

        self.assertEqual(financial.agent_name, "Financial Agent")
        self.assertEqual(marketing.agent_name, "Marketing Agent")
        self.assertEqual(legal.agent_name, "Legal Agent")

        self.assertNotEqual(
            {
                ref.evidence_id
                for ref in financial.evidence_references
            },
            {
                ref.evidence_id
                for ref in legal.evidence_references
            },
        )
