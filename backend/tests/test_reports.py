"""Report generation tests using clearly labelled demonstration data."""

import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Analysis, Evidence, Startup, Base
from app.workflows.service import create_workflow
from app.workflows.due_diligence_graph import run_due_diligence_workflow


class ReportGenerationTests(unittest.IsolatedAsyncioTestCase):
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
                related_agent="report_test",
                findings=[],
                source_metadata={"demonstration_data": True},
                content_hash="demo-" + title.lower().replace(" ", "-"),
            )
            self.db.add(evidence)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    async def test_report_has_all_required_sections(self):
        workflow = create_workflow(self.db, self.analysis.id, retry_limit=0)
        await run_due_diligence_workflow(
            workflow.id,
            self.db,
            retry_limit=0,
            retry_backoff_seconds=0,
            max_pages=1,
        )
        self.db.expire_all()
        report = self.db.get(type(workflow), workflow.id).report

        self.assertIsNotNone(report)
        titles = [section["title"] for section in report["sections"]]
        self.assertEqual(
            titles,
            [
                "Executive Investment Summary",
                "What Should the Investor Do?",
                "Investment Scorecard",
                "Reasons to Consider Investing",
                "Major Risks and Red Flags",
                "Agent-by-Agent Analysis",
                "Missing Information and Due Diligence Checklist",
                "Evidence and Sources",
                "Final Investor Decision Guidance",
            ],
        )
        self.assertIn(
            report["final_assessment_category"],
            {
                "Proceed to Next Stage",
                "Proceed Conditionally",
                "Hold / Further Investigation Required",
                "Do Not Proceed",
            },
        )
        self.assertTrue(report["detailed_reasoning"] if "detailed_reasoning" in report else True)
        self.assertTrue(report["executive_summary"])
        self.assertTrue(report["investor_questions"])
        self.assertTrue(report["charts"])
        self.assertNotIn("investment_score", report)
        self.assertNotIn("score", report)

    async def test_report_marks_missing_information(self):
        workflow = create_workflow(self.db, self.analysis.id, retry_limit=0)
        await run_due_diligence_workflow(
            workflow.id,
            self.db,
            retry_limit=0,
            retry_backoff_seconds=0,
            max_pages=1,
        )
        self.db.expire_all()
        report = self.db.get(type(workflow), workflow.id).report

        self.assertTrue(report["missing_information"])
        self.assertTrue(report["information_gaps"]["tables"])
        self.assertTrue(report["investor_questions"])


if __name__ == "__main__":
    unittest.main()
