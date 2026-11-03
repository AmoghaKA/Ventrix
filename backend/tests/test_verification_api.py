"""API tests for the Verification Agent using demo data only."""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Analysis, Evidence, Startup
from app.db.session import Base, get_db
from app.main import app


class VerificationApiTests(unittest.TestCase):
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

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_evidence(self, title, category, text, status="verified"):
        evidence = Evidence(
            startup_id=self.startup.id,
            analysis_id=self.analysis.id,
            source_url=(
                "https://demo.ventrix.example/"
                + title.lower().replace(" ", "-")
            ),
            source_title=f"[DEMO] {title}",
            source_category=category,
            extracted_information=f"DEMO DATA ONLY. {text}",
            raw_text=f"DEMO DATA ONLY. {text}",
            verification_status=status,
            related_agent="verification_api_test",
            findings=[],
            source_metadata={"demonstration_data": True},
            content_hash="demo-" + title.lower().replace(" ", "-"),
        )
        self.db.add(evidence)
        self.db.commit()

    def add_all_demo_evidence(self):
        self.add_evidence(
            "Seed announcement",
            "financial",
            "DemoCo raised a $1.5 million seed round and reported annual recurring revenue of $2.4 million.",
        )
        self.add_evidence(
            "Market brief",
            "marketing",
            "The workflow automation industry has a growing market size and demand is strongest among mid-sized finance teams.",
        )
        self.add_evidence(
            "Registry extract",
            "legal",
            "DemoCo is registered in Delaware under company number 1234567.",
        )

    def test_verify_endpoint_returns_structured_report(self):
        self.add_all_demo_evidence()

        response = self.client.post(
            f"/api/v1/analyses/{self.analysis.id}/verify"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["analysis_id"], self.analysis.id)
        self.assertIn(
            payload["verification_status"],
            ["VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED", "UNAVAILABLE"],
        )
        self.assertIn("claims_reviewed", payload)
        self.assertIn("supporting_evidence", payload)
        self.assertIn("unsupported_claims", payload)
        self.assertIn("contradictions", payload)
        self.assertIn("source_reliability", payload)
        self.assertIn("missing_evidence", payload)
        self.assertIn("detailed_reasoning", payload)
        self.assertIn("investor_impact", payload)
        self.assertTrue(payload["source_reliability"])
        self.assertTrue(payload["detailed_reasoning"])

    def test_verify_aliases(self):
        self.add_all_demo_evidence()

        for path in (
            f"/api/v1/analyses/{self.analysis.id}/verification/run",
            f"/api/v1/analyses/{self.analysis.id}/agents/verification/run",
        ):
            response = self.client.post(path)
            self.assertEqual(response.status_code, 200, path)

    def test_verify_missing_analysis_returns_404(self):
        response = self.client.post("/api/v1/analyses/999999/verify")
        self.assertEqual(response.status_code, 404)

    def test_latest_verification_from_workflow(self):
        self.add_all_demo_evidence()

        from unittest.mock import patch

        # Start workflow through the API so verification is persisted.
        with patch("app.workflows.service.SessionLocal", self.Session):
            start = self.client.post(
                f"/api/v1/analyses/{self.analysis.id}/start",
                params={"retry_limit": 0, "max_pages": 1},
            )
        self.assertEqual(start.status_code, 200)

        response = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/verification"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis_id"], self.analysis.id)


if __name__ == "__main__":
    unittest.main()
