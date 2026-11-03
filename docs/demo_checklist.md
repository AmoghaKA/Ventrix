# VENTRIX Demo Checklist

## Backend
- [ ] Backend starts without errors
- [ ] GET /health returns healthy
- [ ] GET /db-test returns connected
- [ ] Supabase tables created from supabase_schema.sql

## Startup and analysis
- [ ] POST /api/startup creates a startup
- [ ] Invalid website returns 422
- [ ] Missing startup name returns 422
- [ ] POST /api/analysis/start returns analysis_id
- [ ] Workflow reaches completed or failed
- [ ] Report is available after completion

## Agents and LLM
- [ ] Controller Agent runs with mock agents
- [ ] LLM fallback works
- [ ] Invalid JSON falls back
- [ ] No API keys in frontend

## Usage limits
- [ ] 10 successful runs enforced
- [ ] Failed runs do not count
- [ ] Concurrent requests do not exceed limit
- [ ] GET /api/system/usage returns remaining

## Frontend
- [ ] Startup form submits successfully
- [ ] Analysis ID displayed
- [ ] Status refreshes
- [ ] Agent results displayed
- [ ] Report page loads
- [ ] Usage indicator updates
- [ ] Analysis history loads

## Tests
- [ ] python -m pytest -q
- [ ] Frontend npm run build
