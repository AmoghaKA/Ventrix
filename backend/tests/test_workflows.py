"""Workflow tests using clearly labelled demonstration data only."""

import asyncio
import time
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.controller import WORKFLOW_STEPS
from app.agents.financial import FinancialAgent
from app.agents.legal import LegalAgent
from app.agents.marketing import MarketingAgent
from app.db.models import (
    Analysis,
    DueDiligenceWorkflow,
    Evidence,
    Startup,
    WorkflowActivityLog,
    WorkflowAgentStatus,
    WorkflowCheckpoint,
)
from app.db.session import Base
from app.workflows.due_diligence_graph import run_due_diligence_workflow
from app.workflows.service import create_workflow


class WorkflowTestCase(unittest.IsolatedAsyncioTestCase):
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
            related_agent="workflow_test",
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

    async def run_workflow(self, retry_limit=0, max_pages=1):
        workflow = create_workflow(
            self.db,
            self.analysis.id,
            retry_limit=retry_limit,
        )
        final_state = await run_due_diligence_workflow(
            workflow.id,
            self.db,
            retry_limit=retry_limit,
            retry_backoff_seconds=0,
            max_pages=max_pages,
        )
        self.db.expire_all()
        return workflow.id, final_state

    def statuses(self, workflow_id):
        rows = (
            self.db.query(WorkflowAgentStatus)
            .filter(WorkflowAgentStatus.workflow_id == workflow_id)
            .order_by(WorkflowAgentStatus.sequence)
            .all()
        )
        return {row.agent_key: row for row in rows}

    async def test_full_workflow_completes_and_persists_every_stage(self):
        self.add_all_demo_evidence()

        workflow_id, final_state = await self.run_workflow()

        workflow = self.db.get(DueDiligenceWorkflow, workflow_id)
        statuses = self.statuses(workflow_id)

        self.assertEqual(final_state["workflow_status"], "COMPLETED")
        self.assertEqual(workflow.status, "COMPLETED")
        self.assertEqual(workflow.current_step, "completed")
        self.assertIsNotNone(workflow.started_at)
        self.assertIsNotNone(workflow.completed_at)
        self.assertIsNotNone(workflow.report)
        self.assertEqual(workflow.startup_id, self.startup.id)
        self.assertEqual(self.analysis.status, "completed")
        self.assertEqual(
            set(statuses),
            {key for key, _, _ in WORKFLOW_STEPS},
        )
        for row in statuses.values():
            self.assertEqual(row.status, "COMPLETED", row.agent_key)
            self.assertIsNotNone(row.completed_at, row.agent_key)
        self.assertGreaterEqual(
            statuses["controller"].completed_at,
            statuses["report"].completed_at,
        )
        self.assertEqual(
            set(statuses["data_retrieval"].output),
            {"status", "existing_evidence"},
        )
        self.assertEqual(
            statuses["data_retrieval"].output["status"],
            "SKIPPED",
        )
        self.assertGreater(
            self.db.query(WorkflowCheckpoint)
            .filter(WorkflowCheckpoint.workflow_id == workflow_id)
            .count(),
            0,
        )

        events = {
            row.event
            for row in self.db.query(WorkflowActivityLog)
            .filter(WorkflowActivityLog.workflow_id == workflow_id)
            .all()
        }
        self.assertIn("workflow_started", events)
        self.assertIn("data_retrieval_skipped", events)
        self.assertIn("verification_completed", events)
        self.assertIn("workflow_completed", events)
        self.assertEqual(
            workflow.report["failed_agents"],
            [],
        )

    async def test_specialist_agents_overlap_in_parallel(self):
        self.add_all_demo_evidence()
        starts = {}
        finishes = {}
        originals = {
            "financial": FinancialAgent.execute,
            "marketing": MarketingAgent.execute,
            "legal": LegalAgent.execute,
        }

        def wrapper(key):
            async def execute(agent, startup_id, context):
                starts[key] = time.monotonic()
                await asyncio.sleep(0.08)
                result = await originals[key](agent, startup_id, context)
                finishes[key] = time.monotonic()
                return result

            return execute

        with patch.object(FinancialAgent, "execute", wrapper("financial")), patch.object(
            MarketingAgent, "execute", wrapper("marketing")
        ), patch.object(LegalAgent, "execute", wrapper("legal")):
            await self.run_workflow()

        self.assertEqual(set(starts), {"financial", "marketing", "legal"})
        self.assertLess(max(starts.values()), min(finishes.values()))

    async def test_specialist_retries_then_succeeds(self):
        self.add_all_demo_evidence()
        original = FinancialAgent.execute
        calls = {"count": 0}

        async def flaky(agent, startup_id, context):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary demo failure")
            return await original(agent, startup_id, context)

        with patch.object(FinancialAgent, "execute", flaky):
            workflow_id, final_state = await self.run_workflow(retry_limit=2)

        statuses = self.statuses(workflow_id)
        self.assertEqual(final_state["workflow_status"], "COMPLETED")
        self.assertEqual(calls["count"], 2)
        self.assertEqual(statuses["financial"].status, "COMPLETED")
        self.assertEqual(statuses["financial"].attempt_count, 2)

    async def test_all_specialists_failing_marks_workflow_failed(self):
        self.add_all_demo_evidence()

        async def always_fail(agent, startup_id, context):
            raise RuntimeError("demo specialist failure")

        with patch.object(FinancialAgent, "execute", always_fail), patch.object(
            MarketingAgent, "execute", always_fail
        ), patch.object(LegalAgent, "execute", always_fail):
            workflow_id, final_state = await self.run_workflow(retry_limit=1)

        workflow = self.db.get(DueDiligenceWorkflow, workflow_id)
        statuses = self.statuses(workflow_id)

        self.assertEqual(final_state["workflow_status"], "FAILED")
        self.assertEqual(workflow.status, "FAILED")
        self.assertEqual(workflow.current_step, "failed")
        self.assertEqual(self.analysis.status, "failed")
        self.assertIn("All specialist agents failed", workflow.error_details)
        for key in ("financial", "marketing", "legal"):
            self.assertEqual(statuses[key].status, "FAILED")
            self.assertEqual(statuses[key].attempt_count, 2)
        self.assertEqual(statuses["controller"].status, "FAILED")

    async def test_partial_specialist_failure_still_generates_report(self):
        self.add_all_demo_evidence()

        async def always_fail(agent, startup_id, context):
            raise RuntimeError("demo financial failure")

        with patch.object(FinancialAgent, "execute", always_fail):
            workflow_id, final_state = await self.run_workflow(retry_limit=0)

        workflow = self.db.get(DueDiligenceWorkflow, workflow_id)
        statuses = self.statuses(workflow_id)

        self.assertEqual(final_state["workflow_status"], "COMPLETED")
        self.assertEqual(workflow.status, "COMPLETED")
        self.assertEqual(statuses["financial"].status, "FAILED")
        self.assertEqual(statuses["marketing"].status, "COMPLETED")
        self.assertEqual(statuses["legal"].status, "COMPLETED")
        self.assertEqual(workflow.report["failed_agents"], ["financial"])
        self.assertEqual(
            statuses["controller"].status,
            "COMPLETED",
        )
