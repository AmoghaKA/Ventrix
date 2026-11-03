# Ventrix Architecture

## Overview

Ventrix is a full-stack startup due diligence platform. The frontend is a Next.js application. The backend is a FastAPI service backed by SQLite and SQLAlchemy. LangGraph orchestrates the due diligence workflow.

## Backend Components

- `app/main.py`: FastAPI application, CORS, startup database initialization.
- `app/api/__init__.py`: REST endpoints for analyses, evidence, agents, workflows, verification, reports, and system status.
- `app/agents/`: Financial, Marketing, Legal, Verification, and Controller agents.
- `app/data/`: Public data retrieval, extraction, caching, and evidence storage.
- `app/workflows/`: LangGraph workflow, controller orchestration, report generation, and background execution.
- `app/llm/gateway.py`: Backend-only LLM provider gateway with Gemini, NVIDIA Nemotron, and Mistral fallback.
- `app/db/models.py`: SQLAlchemy models for analyses, startups, evidence, workflows, statuses, logs, checkpoints, and cache entries.

## Workflow

1. Create an analysis.
2. Start the workflow.
3. Retrieve or reuse public evidence.
4. Run Financial, Marketing, and Legal agents in parallel.
5. Run the Verification Agent.
6. Generate the comprehensive investor report.
7. Persist statuses, logs, checkpoints, and report.
8. Retrieve or download the report.

## Data Flow

The frontend calls FastAPI endpoints only. LLM provider credentials remain in backend environment variables. Agent findings reference stored evidence IDs. Missing information is reported explicitly instead of estimated.

## Security

- API keys are backend-only.
- CORS origins are configured through `CORS_ORIGINS`.
- Inputs are validated with Pydantic schemas.
- Errors are handled without exposing internal details.
