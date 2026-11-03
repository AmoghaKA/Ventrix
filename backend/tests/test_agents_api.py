"""API tests for agent orchestration using clearly labelled demo data."""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Analysis, Evidence, Startup
from app.db.session import Base, get_db
from app.main import app


class AgentApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.analysis = Analysis(
            startup_name="DemoCo",
            website="https://demo.ventrix.example",
            industry="Workflow software",
            status="pending",
        )
        self.db.add(self.analysis)
        self.db.commit()
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

    def add_evidence(self, title, category, text, status="unverified"):
        startup = (
            self.db.query(Startup)
            .filter(Startup.website == "https://demo.ventrix.example")
            .one_or_none()
        )
        if startup is None:
            startup = Startup(
                name="DemoCo",
                website="https://demo.ventrix.example",
                industry="Workflow software",
            )
            self.db.add(startup)
            self.db.flush()

        evidence = Evidence(
            startup_id=startup.id,
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
            related_agent="orchestration_test",
            findings=[],
            source_metadata={"demonstration_data": True},
            content_hash="demo-" + title.lower().replace(" ", "-"),
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def add_all_demo_evidence(self):
        self.add_evidence(
            "Seed announcement",
            "financial",
            (
                "DemoCo raised a $1.5 million seed round and reported annual "
                "recurring revenue of $2.4 million."
            ),
            status="verified",
        )
        self.add_evidence(
            "Market brief",
            "marketing",
            (
                "The workflow automation industry has a growing market size "
                "and demand is strongest among mid-sized finance teams."
            ),
            status="verified",
        )
        self.add_evidence(
            "Registry extract",
            "legal",
            (
                "DemoCo is registered in Delaware under company number "
                "1234567."
            ),
            status="verified",
        )

    def test_lists_available_agents(self):
        response = self.client.get("/api/v1/agents")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["key"] for item in response.json()],
            ["financial", "marketing", "legal"],
        )

    def test_runs_single_agent(self):
        evidence = self.add_evidence(
            "Seed announcement",
            "financial",
            (
                "DemoCo raised a $1.5 million seed round and reported annual "
                "recurring revenue of $2.4 million."
            ),
            status="verified",
        )

        response = self.client.post(
            f"/api/v1/analyses/{self.analysis.id}/agents/financial/run"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["agent_name"], "Financial Agent")
        self.assertEqual(payload["analysis_id"], self.analysis.id)
        self.assertEqual(payload["execution_status"], "PARTIAL")
        self.assertIn(
            evidence.id,
            [reference["evidence_id"] for reference in payload["evidence_references"]],
        )

    def test_accepts_related_agent_alias(self):
        self.add_evidence(
            "Market brief",
            "marketing",
            (
                "The workflow automation industry has a growing market size "
                "and demand is strongest among mid-sized finance teams."
            ),
            status="verified",
        )

        response = self.client.post(
            f"/api/v1/analyses/{self.analysis.id}/agents/"
            "market_analysis_agent/run"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent_name"], "Marketing Agent")

    def test_runs_all_agents_and_reuses_startup(self):
        self.add_all_demo_evidence()

        first = self.client.post(
            f"/api/v1/analyses/{self.analysis.id}/agents/run"
        )
        second = self.client.post(
            f"/api/v1/analyses/{self.analysis.id}/agents/run"
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        payload = first.json()
        self.assertEqual(payload["analysis_id"], self.analysis.id)
        self.assertGreater(payload["startup_id"], 0)
        self.assertEqual(
            [output["agent_name"] for output in payload["outputs"]],
            ["Financial Agent", "Marketing Agent", "Legal Agent"],
        )
        self.assertEqual(self.db.query(Startup).count(), 1)
        self.assertEqual(
            {output["analysis_id"] for output in payload["outputs"]},
            {self.analysis.id},
        )

    def test_batch_can_select_agents(self):
        self.add_all_demo_evidence()

        response = self.client.post(
            f"/api/v1/analyses/{self.analysis.id}/agents/run",
            params=[("agents", "financial"), ("agents", "legal")],
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [output["agent_name"] for output in response.json()["outputs"]],
            ["Financial Agent", "Legal Agent"],
        )

    def test_unknown_agent_returns_404(self):
        response = self.client.post(
            f"/api/v1/analyses/{self.analysis.id}/agents/unknown/run"
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("Supported agents", response.json()["detail"])

    def test_missing_analysis_returns_404(self):
        response = self.client.post(
            "/api/v1/analyses/999999/agents/financial/run"
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("was not found", response.json()["detail"])
