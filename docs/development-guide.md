# Development Guide

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests

Backend:

```bash
cd backend
python -m unittest discover -s tests -q
```

Frontend:

```bash
cd frontend
npm run build
```

## Environment Variables

Configure LLM providers in `backend/.env`:

- `GEMINI_API_KEY`
- `NVIDIA_API_KEY`
- `MISTRAL_API_KEY`

Never commit real API keys. The frontend must not contain provider credentials.

## Usage Limit

The backend enforces a maximum of 10 analyses by default. Change `MAX_ANALYSES` in settings or `.env` if needed.