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

## Notes

- API keys are backend-only and never exposed to the frontend.
- Agents and workflows are scaffolded but not yet implemented.
- SQLite database is created automatically on startup.
