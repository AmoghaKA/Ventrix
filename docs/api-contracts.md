# API Contracts

Base URL: `http://localhost:8000/api/v1`

## Analyses

- `POST /analyses` - Create an analysis.
- `GET /analyses` - List analyses.
- `GET /analyses/{analysis_id}` - Get an analysis.
- `POST /analyses/{analysis_id}/collect-evidence` - Retrieve and store public evidence.
- `POST /analyses/{analysis_id}/start` - Start the due diligence workflow.

## Evidence

- `GET /evidence` - Search stored evidence.
- `GET /evidence/{evidence_id}` - Get a stored evidence record.

## Agents

- `GET /agents` - List available specialist agents.
- `POST /analyses/{analysis_id}/agents/{agent_key}/run` - Run one agent.
- `POST /analyses/{analysis_id}/agents/run` - Run all or selected agents.
- `POST /analyses/{analysis_id}/verify` - Run the Verification Agent.

## Workflows

- `GET /analyses/{analysis_id}/workflow` - Get latest workflow status.
- `GET /analyses/{analysis_id}/workflow/agents` - Get per-agent statuses.
- `GET /analyses/{analysis_id}/workflow/logs` - Get activity logs.

## Verification

- `GET /analyses/{analysis_id}/verification` - Get latest verification report.

## Reports

- `GET /analyses/{analysis_id}/report` - Get generated investor report.
- `GET /analyses/{analysis_id}/report/pdf` - Download report as PDF.

## System

- `GET /system/status` - Get analysis usage and provider status.
- `GET /system/llm` - Get LLM provider status, usage, and fallback history.

## Error Responses

Errors use JSON objects with a `detail` field. Validation errors return HTTP 422. Missing resources return HTTP 404. Usage-limit violations return HTTP 403.