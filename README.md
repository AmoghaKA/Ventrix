# Ventrix

AI-powered startup due diligence platform built from an investor's perspective.

## Tech Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI
- **AI Orchestration:** LangGraph
- **Data Validation:** Pydantic
- **Database:** SQLite
- **LLM Providers:** Gemini (primary), NVIDIA Nemotron (secondary), Mistral (fallback)

## Project Structure

```
Ventrix/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings
│   │   │   └── logging.py       # Logging setup
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── session.py       # SQLAlchemy engine & session
│   │   ├── schemas/
│   │   │   └── __init__.py      # Pydantic schemas
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── base.py          # BaseAgent class
│   │   └── api/
│   │       └── __init__.py      # API router
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   ├── lib/
│   │   └── api.ts               # API client
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   └── next.config.js
└── README.md
```

## Backend Setup

### 1. Create virtual environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your LLM API keys
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Health check: `GET http://localhost:8000/health`

## Frontend Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Run the development server

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/health` | API health check |
| POST | `/api/v1/analyses` | Create an analysis |
| GET | `/api/v1/analyses` | List analyses |
| GET | `/api/v1/analyses/{analysis_id}` | Get an analysis |
| POST | `/api/v1/analyses/{analysis_id}/collect-evidence` | Retrieve and store public evidence |
| GET | `/api/v1/evidence` | Search stored evidence |
| GET | `/api/v1/evidence/{evidence_id}` | Get a stored evidence record |
| GET | `/api/v1/agents` | List available specialist agents |
| POST | `/api/v1/analyses/{analysis_id}/agents/{agent_key}/run` | Run one agent |
| POST | `/api/v1/analyses/{analysis_id}/agents/run` | Run all or selected agents |
| POST | `/api/v1/analyses/{analysis_id}/start` | Start the due diligence workflow |
| GET | `/api/v1/analyses/{analysis_id}/workflow` | Get the latest workflow status and report |
| GET | `/api/v1/analyses/{analysis_id}/workflow/agents` | Get per-agent workflow statuses |
| GET | `/api/v1/analyses/{analysis_id}/workflow/logs` | Get workflow activity logs |

Agent keys are `financial`, `marketing`, and `legal`. The batch endpoint accepts repeated `agents` query parameters to select a subset.

Workflow aliases are also available at `/api/v1/analyses/{analysis_id}/workflow/start` and `/api/v1/analyses/{analysis_id}/workflow/status`.

## Due Diligence Workflow

Starting an analysis runs the LangGraph workflow:

1. Data retrieval
2. Controller Agent
3. Financial, Marketing, and Legal agents in parallel
4. Verification Agent
5. Final report

Workflow and agent statuses use `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED`. Specialist failures are retried up to the configured workflow retry limit. If all specialists fail, the workflow fails; partial failures are retained in the final report. Existing evidence is reused instead of performing another retrieval.

## Notes

- API keys are backend-only and never exposed to the frontend.
- Financial, marketing, and legal agents are implemented with structured, evidence-backed output.
- The Controller Agent, LangGraph workflow, verification, persisted statuses/logs/checkpoints, and deterministic final report are implemented.
- LLM provider integration is not yet implemented; the current workflow uses the existing retrieval and evidence-backed agent pipeline.
- SQLite database is created automatically on startup.
