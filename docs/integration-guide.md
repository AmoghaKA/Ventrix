# Integration Guide

## Frontend to Backend

The frontend uses `frontend/lib/api.ts` for all backend communication. The API base URL is controlled by `NEXT_PUBLIC_API_BASE_URL`.

## Running Locally

1. Start the backend on `http://localhost:8000`.
2. Start the frontend on `http://localhost:3000`.
3. Create an analysis in the UI.
4. Open the analysis monitoring page.
5. Start the workflow.
6. Review agent outputs, verification, evidence, and the investor report.

## Workflow Integration

The frontend polls workflow status, agent statuses, and activity logs. Report retrieval and PDF download use the report endpoints. Evidence Explorer uses the evidence search endpoint.

## LLM Integration

LLM provider calls are backend-only. The frontend never calls Gemini, NVIDIA, or Mistral directly. Provider status and fallback history are available through `/system/llm`.