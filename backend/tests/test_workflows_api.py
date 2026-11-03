"""API tests for the due diligence workflow using demo data only."""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Analysis, Evidence, Startup
from app.db.session import Base, get_db
from app.main import app


class WorkflowApiTests(unittest.TestCase):
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

    def add_evidence(self, title, category, text):
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
            verification_status="verified",
            related_agent="workflow_api_test",
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
            (
                "DemoCo raised a $1.5 million seed round and reported annual "
                "recurring revenue of $2.4 million."
            ),
        )
        self.add_evidence(
            "Market brief",
            "marketing",
            (
                "The workflow automation industry has a growing market size "
                "and demand is strongest among mid-sized finance teams."
            ),
        )
        self.add_evidence(
            "Registry extract",
            "legal",
            (
                "DemoCo is registered in Delaware under company number "
                "1234567."
            ),
        )

    def start_workflow(self, **kwargs):
        with patch(
            "app.workflows.service.SessionLocal",
            self.Session,
        ):
            response = self.client.post(
                f"/api/v1/analyses/{self.analysis.id}/start",
                params=kwargs,
            )
        self.db.expire_all()
        return response

    def test_start_runs_workflow_and_status_agents_and_logs_are_available(self):
        self.add_all_demo_evidence()

        response = self.start_workflow(retry_limit=0, max_pages=1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")
        workflow_id = response.json()["id"]

        status = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/workflow"
        )
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["id"], workflow_id)
        self.assertEqual(status.json()["status"], "COMPLETED")
        self.assertIsNotNone(status.json()["report"])

        agents = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/workflow/agents"
        )
        self.assertEqual(agents.status_code, 200)
        self.assertEqual(
            [item["agent_key"] for item in agents.json()],
            [
                "data_retrieval",
                "controller",
                "financial",
                "marketing",
                "legal",
                "verification",
                "report",
            ],
        )
        for item in agents.json():
            self.assertEqual(item["status"], "COMPLETED", item["agent_key"])
        self.assertEqual(agents.json()[0]["output"]["status"], "SKIPPED")

        logs = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/workflow/logs",
            params={"limit": 100},
        )
        self.assertEqual(logs.status_code, 200)
        events = [item["event"] for item in logs.json()]
        self.assertIn("workflow_started", events)
        self.assertIn("workflow_completed", events)

    def test_duplicate_start_is_rejected_while_workflow_is_active(self):
        with patch(
            "app.api.run_workflow_background",
            new=AsyncMock(),
        ):
            first = self.client.post(
                f"/api/v1/analyses/{self.analysis.id}/start"
            )
            second = self.client.post(
                f"/api/v1/analyses/{self.analysis.id}/start"
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "PENDING")
        self.assertEqual(second.status_code, 409)
        self.assertIn("already", second.json()["detail"])

    def test_start_aliases_and_missing_analysis(self):
        self.add_all_demo_evidence()

        with patch(
            "app.api.run_workflow_background",
            new=AsyncMock(),
        ):
            alias = self.client.post(
                f"/api/v1/analyses/{self.analysis.id}/workflow/start"
            )
        missing = self.client.post("/api/v1/analyses/999999/start")

        self.assertEqual(alias.status_code, 200)
        self.assertEqual(missing.status_code, 404)
        self.assertIn("was not found", missing.json()["detail"])

    def test_missing_workflow_endpoints_return_404(self):
        for suffix in ("workflow", "workflow/status", "workflow/agents", "workflow/logs"):
            response = self.client.get(
                f"/api/v1/analyses/{self.analysis.id}/{suffix}"
            )
            self.assertEqual(response.status_code, 404, suffix)

    def test_status_and_agents_aliases(self):
        self.add_all_demo_evidence()

        self.start_workflow(retry_limit=0, max_pages=1)

        status = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/workflow/status"
        )
        agents = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/workflow/agents"
        )

        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "COMPLETED")
        self.assertEqual(agents.status_code, 200)
        self.assertEqual(len(agents.json()), 7)
