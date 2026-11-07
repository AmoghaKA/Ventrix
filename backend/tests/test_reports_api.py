"""API tests for report retrieval and PDF export using demo data only."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Analysis, Evidence, Startup
from app.db.session import Base, get_db
from app.main import app


class ReportApiTests(unittest.TestCase):
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

        for title, category, text in (
            (
                "Seed announcement",
                "financial",
                "DemoCo raised a $1.5 million seed round and reported annual recurring revenue of $2.4 million.",
            ),
            (
                "Market brief",
                "marketing",
                "The workflow automation industry has a growing market size and demand is strongest among mid-sized finance teams.",
            ),
            (
                "Registry extract",
                "legal",
                "DemoCo is registered in Delaware under company number 1234567.",
            ),
        ):
            evidence = Evidence(
                startup_id=self.startup.id,
                analysis_id=self.analysis.id,
                source_url=f"https://demo.ventrix.example/{title.lower().replace(' ', '-')}",
                source_title=f"[DEMO] {title}",
                source_category=category,
                extracted_information=f"DEMO DATA ONLY. {text}",
                raw_text=f"DEMO DATA ONLY. {text}",
                verification_status="verified",
                related_agent="report_api_test",
                findings=[],
                source_metadata={"demonstration_data": True},
                content_hash="demo-" + title.lower().replace(" ", "-"),
            )
            self.db.add(evidence)
        self.db.commit()

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def start_workflow(self):
        with patch("app.workflows.service.SessionLocal", self.Session):
            response = self.client.post(
                f"/api/v1/analyses/{self.analysis.id}/start",
                params={"retry_limit": 0, "max_pages": 1},
            )
        self.db.expire_all()
        return response

    def test_report_retrieval(self):
        start = self.start_workflow()
        self.assertEqual(start.status_code, 200)

        response = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/report"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["analysis_id"], self.analysis.id)
        self.assertEqual(len(payload["sections"]), 9)
        self.assertIn("final_assessment_category", payload)

    def test_report_pdf_download(self):
        start = self.start_workflow()
        self.assertEqual(start.status_code, 200)

        response = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/report/pdf"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertGreater(len(response.content), 1000)

    def test_missing_report_returns_404(self):
        response = self.client.get(
            f"/api/v1/analyses/{self.analysis.id}/report"
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
