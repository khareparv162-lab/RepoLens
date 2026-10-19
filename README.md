# RepoLens

RepoLens analyzes public GitHub repositories and stores analysis history in PostgreSQL.

## Stack
- Frontend: Next.js, React, TypeScript, Lucide
- Backend: FastAPI, SQLAlchemy 2, asyncpg, PostgreSQL
- Data source: GitHub REST API

## 1. Configure PostgreSQL
Create a PostgreSQL database (Neon is a convenient hosted option). Copy its connection string.

In `backend/.env`, set `DATABASE_URL`. For async SQLAlchemy, the URL should start with:
`postgresql+asyncpg://`

Example:
```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DATABASE?ssl=require
GITHUB_TOKEN=
FRONTEND_ORIGIN=http://localhost:3000
```
Use your provider's exact connection parameters. Never commit `.env`.

## 2. Run the backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```
Open `http://localhost:8000/docs`.

Tables are created automatically on startup for this prototype. For production schema changes, use migrations (e.g. Alembic).

## 3. Run the frontend
In a second terminal:
```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```
Open `http://localhost:3000`.

For macOS/Linux, use `cp .env.example .env` and `cp .env.local.example .env.local` instead of `copy`.

## API
- `GET /api/health` — service and database status
- `GET /api/analyze/{owner}/{repo}` — fetch and save a fresh analysis
- `GET /api/history` — list saved analysis reports
- `GET /api/history/{report_id}` — fetch a saved report

## Notes
- Only public GitHub repositories are supported.
- The repository hygiene score is a simple indicator, not a security audit or a measure of developer skill.
- The current version does not include user accounts or per-user report ownership.
- A GitHub token is optional, but helps with API rate limits. Keep it server-side only.
