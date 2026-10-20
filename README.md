# RepoLens 🔎
### GitHub Repository Analyzer

RepoLens is a full-stack web application that analyzes public GitHub repositories and presents repository health indicators, programming language statistics, recent commits, contributors, and saved analysis history in one place.

It helps developers understand repository structure and documentation practices through a simple, centralized dashboard.

## ✨ Features

- **Repository Analysis** — Analyze public GitHub repositories using their owner and repository name.
- **Repository Health Score** — Evaluate basic repository hygiene using checks for documentation, README, license, tests, and GitHub workflows.
- **Language Statistics** — View the programming languages used in a repository and their relative proportions.
- **Recent Commits** — Inspect recent repository commits and their metadata.
- **Contributor Insights** — View leading contributors and their contribution counts.
- **Analysis History** — Store and retrieve previous analysis reports from the database.
- **Input Validation** — Validate repository identifiers before making external requests.
- **Rate Limiting** — Apply request limits to the repository analysis endpoint.

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI |
| Database | Supabase PostgreSQL |
| Database ORM | SQLAlchemy |
| Database Driver | asyncpg |
| External API | GitHub REST API |
| HTTP Client | HTTPX |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |

## 🏗️ Architecture

```text
User
  │
  ▼
Next.js Frontend (Vercel)
  │
  ▼
FastAPI Backend (Render)
  ├── GitHub REST API
  │     ├── Repository metadata
  │     ├── Languages
  │     ├── Recent commits
  │     ├── Contributors
  │     └── README and repository contents
  │
  ▼
SQLAlchemy + asyncpg
  │
  ▼
Supabase PostgreSQL
  ├── Repository records
  └── Analysis reports
```

## 📊 Repository Health Checks

RepoLens evaluates five basic repository hygiene indicators:

| Check | Purpose |
|---|---|
| Repository Description | Checks whether the repository has a description |
| README Documentation | Checks whether README documentation exists |
| Open-Source License | Checks for a recognized repository license |
| Test Directory | Looks for a conventional test directory |
| GitHub Workflows | Checks for a `.github` directory |

The health score represents the proportion of these checks that pass. It is a repository hygiene indicator, **not a security audit or a measure of developer skill**.

## 🚀 Live Demo

- **Frontend:** https://repo-lens-nine.vercel.app
- **Backend Health Check:** https://repolens-backend-31c4.onrender.com/api/health

## 💻 Run Locally

### Prerequisites

- Python 3.10 or a compatible version
- Node.js and npm
- A Supabase PostgreSQL database
- A GitHub personal access token (optional, but useful for API rate limits)

### 1. Clone the repository

```bash
git clone https://github.com/khareparv162-lab/RepoLens.git
cd RepoLens
```

### 2. Configure the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `backend/.env` file with your own database credentials:

```env
user=YOUR_DATABASE_USER
password=YOUR_DATABASE_PASSWORD
host=YOUR_DATABASE_HOST
port=5432
dbname=YOUR_DATABASE_NAME
GITHUB_TOKEN=YOUR_GITHUB_TOKEN
FRONTEND_ORIGIN=http://localhost:3000
```

Keep your actual `.env` file private and never commit credentials to GitHub.

Start the backend:

```bash
python -m uvicorn main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Configure the frontend

Open another terminal:

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open `http://localhost:3000` in your browser.

## 🔐 Security Notes

- Keep database credentials and GitHub tokens in environment variables.
- Do not commit `.env` or `.env.local` files.
- Use environment-specific configuration for local and production deployments.
- The frontend API URL is public configuration; never put private credentials in frontend environment variables.

## 🧪 Testing

The backend includes automated tests for core API behavior. Run the test suite from the backend directory:

```bash
pytest
```

## 🔮 Future Improvements

- Add more detailed repository quality metrics.
- Improve visualizations for repository activity and language distribution.
- Add filtering and search for saved analysis reports.
- Expand automated tests and continuous integration.
- Introduce optional repository comparison features.

## 👨‍💻 Author

**Parv Khare**

Computer Science Engineering — Artificial Intelligence and Machine Learning

- GitHub: [@khareparv162-lab](https://github.com/khareparv162-lab)

---

*RepoLens — Understand your repository at a glance.*
