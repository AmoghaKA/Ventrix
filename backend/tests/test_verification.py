"""Verification Agent tests using clearly labelled demonstration data."""

import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.output import (
    AgentFinding,
    AgentOutput,
    EvidenceStatus,
    ExecutionStatus,
    RiskLevel,
)
from app.agents.verification import (
    VerificationAgent,
    VerificationStatus,
)
from app.db.models import Analysis, Evidence, Startup, Base


class VerificationAgentTests(unittest.IsolatedAsyncioTestCase):
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

    def add_evidence(self, title, status="verified"):
        evidence = Evidence(
            startup_id=self.startup.id,
            analysis_id=self.analysis.id,
            source_url=f"https://demo.ventrix.example/{title.lower().replace(' ', '-')}",
            source_title=f"[DEMO] {title}",
            source_category="financial",
            extracted_information="DEMO DATA ONLY. DemoCo raised funding.",
            raw_text="DEMO DATA ONLY. DemoCo raised funding.",
            verification_status=status,
            related_agent="verification_test",
            findings=[],
            source_metadata={"demonstration_data": True},
            content_hash="demo-" + title.lower().replace(" ", "-"),
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    async def test_verified_claim_with_stored_evidence(self):
        evidence = self.add_evidence("Seed announcement", "verified")
        output = AgentOutput(
            agent_name="Financial Agent",
            analysis_id=self.analysis.id,
            findings=[
                AgentFinding(
                    dimension="Funding history",
                    summary="Funding evidence exists.",
                    explanation="Funding evidence exists.",
                    risk_level=RiskLevel.LOW,
                    evidence_status=EvidenceStatus.VERIFIED,
                    evidence_references=[evidence.id],
                    investor_impact="Low impact.",
                )
            ],
            investor_impact="Low impact.",
        )

        result = await VerificationAgent(self.db).execute(
            self.startup.id,
            {
                "analysis_id": self.analysis.id,
                "specialist_outputs": {"financial": output},
                "specialist_errors": {},
            },
        )

        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(result.total_findings, 1)
        self.assertEqual(result.checked_references, 1)
        self.assertEqual(result.valid_references, 1)
        self.assertEqual(result.invalid_references, 0)
        self.assertEqual(len(result.claims_reviewed), 1)
        self.assertEqual(
            result.claims_reviewed[0].verification_status,
            VerificationStatus.VERIFIED,
        )
        self.assertTrue(result.supporting_evidence)
        self.assertTrue(result.source_reliability)
        self.assertTrue(result.detailed_reasoning)
        self.assertTrue(result.investor_impact)

    async def test_unsupported_overstated_claim(self):
        evidence = self.add_evidence("Seed announcement", "unverified")
        output = AgentOutput(
            agent_name="Financial Agent",
            analysis_id=self.analysis.id,
            findings=[
                AgentFinding(
                    dimension="Funding history",
                    summary="Funding evidence is verified.",
                    explanation="Funding evidence is verified.",
                    risk_level=RiskLevel.LOW,
                    evidence_status=EvidenceStatus.VERIFIED,
                    evidence_references=[evidence.id],
                    investor_impact="Low impact.",
                )
            ],
            investor_impact="Low impact.",
        )

        result = await VerificationAgent(self.db).execute(
            self.startup.id,
            {
                "analysis_id": self.analysis.id,
                "specialist_outputs": {"financial": output},
                "specialist_errors": {},
            },
        )

        self.assertEqual(result.status, VerificationStatus.UNVERIFIED)
        self.assertTrue(result.unsupported_claims)
        self.assertEqual(result.claims_reviewed[0].verification_status, VerificationStatus.UNVERIFIED)
        self.assertIn("overstated", result.claims_reviewed[0].reasoning)

    async def test_missing_evidence_is_reported(self):
        output = AgentOutput(
            agent_name="Financial Agent",
            analysis_id=self.analysis.id,
            findings=[
                AgentFinding(
                    dimension="Funding history",
                    summary="Funding evidence is verified.",
                    explanation="Funding evidence is verified.",
                    risk_level=RiskLevel.LOW,
                    evidence_status=EvidenceStatus.VERIFIED,
                    evidence_references=[999999],
                    investor_impact="Low impact.",
                )
            ],
            investor_impact="Low impact.",
            missing_information=["No funding evidence."],
        )

        result = await VerificationAgent(self.db).execute(
            self.startup.id,
            {
                "analysis_id": self.analysis.id,
                "specialist_outputs": {"financial": output},
                "specialist_errors": {"legal": "Legal agent failed."},
            },
        )

        self.assertEqual(result.invalid_references, 1)
        self.assertTrue(result.missing_evidence)
        self.assertIn("legal", str(result.missing_evidence).lower())
        self.assertTrue(any("999999" in item for item in result.missing_evidence))

    async def test_contradiction_detection(self):
        evidence = self.add_evidence("Shared evidence", "verified")
        financial = AgentOutput(
            agent_name="Financial Agent",
            analysis_id=self.analysis.id,
            risk_level=RiskLevel.CRITICAL,
            findings=[
                AgentFinding(
                    dimension="Profitability",
                    summary="The company is profitable.",
                    explanation="The company is profitable.",
                    risk_level=RiskLevel.CRITICAL,
                    evidence_status=EvidenceStatus.VERIFIED,
                    evidence_references=[evidence.id],
                    investor_impact="High impact.",
                )
            ],
            investor_impact="High impact.",
        )
        marketing = AgentOutput(
            agent_name="Marketing Agent",
            analysis_id=self.analysis.id,
            risk_level=RiskLevel.LOW,
            findings=[
                AgentFinding(
                    dimension="Market trends",
                    summary="The company is unprofitable and has net loss.",
                    explanation="The company is unprofitable and has net loss.",
                    risk_level=RiskLevel.LOW,
                    evidence_status=EvidenceStatus.VERIFIED,
                    evidence_references=[evidence.id],
                    investor_impact="Low impact.",
                )
            ],
            investor_impact="Low impact.",
        )

        result = await VerificationAgent(self.db).execute(
            self.startup.id,
            {
                "analysis_id": self.analysis.id,
                "specialist_outputs": {
                    "financial": financial,
                    "marketing": marketing,
                },
                "specialist_errors": {},
            },
        )

        self.assertEqual(result.status, VerificationStatus.CONTRADICTED)
        self.assertTrue(result.contradictions)
        self.assertTrue(result.unsupported_claims)

    async def test_source_reliability_scores(self):
        verified = self.add_evidence("Verified source", "verified")
        unverified = self.add_evidence("Unverified source", "unverified")

        result = await VerificationAgent(self.db).execute(
            self.startup.id,
            {
                "analysis_id": self.analysis.id,
                "specialist_outputs": {},
                "specialist_errors": {},
            },
        )

        scores = {item.evidence_id: item.reliability_score for item in result.source_reliability}
        self.assertGreater(scores[verified.id], scores[unverified.id])
        self.assertEqual(
            next(item.reliability_level for item in result.source_reliability if item.evidence_id == verified.id),
            "HIGH",
        )

    async def test_no_outputs_fails(self):
        result = await VerificationAgent(self.db).execute(
            self.startup.id,
            {
                "analysis_id": self.analysis.id,
                "specialist_outputs": {},
                "specialist_errors": {},
            },
        )

        self.assertEqual(result.execution_status, ExecutionStatus.FAILED)
        self.assertEqual(result.status, VerificationStatus.UNAVAILABLE)
        self.assertTrue(result.missing_evidence)


if __name__ == "__main__":
    unittest.main()
