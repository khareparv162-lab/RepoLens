import asyncio
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any


import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from database import Base, engine, get_db
from models import AnalysisReport, Repository

load_dotenv()

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").strip()
OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="RepoLens API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "RepoLens",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def github_get(client: httpx.AsyncClient, path: str) -> Any:
    try:
        response = await client.get(f"{GITHUB_API}{path}", headers=github_headers())
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise HTTPException(status_code=502, detail="Could not reach the GitHub API.") from exc

    if response.status_code == 404:
        return None
    if response.status_code == 403:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            raise HTTPException(
                status_code=429,
                detail="GitHub API rate limit reached. Add a server-side GITHUB_TOKEN and try again later.",
            )
        raise HTTPException(status_code=502, detail="GitHub denied the API request.")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"GitHub API returned {response.status_code}.")
    return response.json()


def build_health_checks(repo: dict, root_items: list[dict], readme: Any) -> list[dict]:
    root_names = {
        item.get("name", "").lower()
        for item in root_items
        if isinstance(item, dict)
    }
    has_tests = any(
        name in root_names
        for name in ("tests", "test", "__tests__", "spec")
    )
    has_workflows = ".github" in root_names
    checks = [
        {
            "key": "description",
            "label": "Repository description",
            "passed": bool(repo.get("description")),
            "detail": "A short description explains the project's purpose.",
        },
        {
            "key": "readme",
            "label": "README documentation",
            "passed": bool(readme and readme.get("size", 0) > 0),
            "detail": "A README helps visitors understand setup and usage.",
        },
        {
            "key": "license",
            "label": "Open-source license",
            "passed": bool(repo.get("license") and repo["license"].get("spdx_id") not in (None, "NOASSERTION")),
            "detail": "A clear license communicates reuse terms.",
        },
        {
            "key": "tests",
            "label": "Test directory",
            "passed": has_tests,
            "detail": "A conventional test folder makes automated tests easier to find.",
        },
        {
            "key": "workflows",
            "label": "GitHub workflows",
            "passed": has_workflows,
            "detail": "GitHub Actions workflows can automate checks and releases.",
        },
    ]
    return checks


@app.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(select(1))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database connection failed.") from exc


@app.get("/api/analyze/{owner}/{repo}")
@limiter.limit("20/minute")
async def analyze_repository(
    request: Request,
    owner: str,
    repo: str,
    db: AsyncSession = Depends(get_db),
):
    if not OWNER_PATTERN.fullmatch(owner) or not REPO_PATTERN.fullmatch(repo) or repo in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid GitHub owner or repository name.")

    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0)) as client:
        repo_task = github_get(client, f"/repos/{owner}/{repo}")
        languages_task = github_get(client, f"/repos/{owner}/{repo}/languages")
        commits_task = github_get(client, f"/repos/{owner}/{repo}/commits?per_page=5")
        contributors_task = github_get(client, f"/repos/{owner}/{repo}/contributors?per_page=5")
        readme_task = github_get(client, f"/repos/{owner}/{repo}/readme")
        contents_task = github_get(client, f"/repos/{owner}/{repo}/contents")

        repository_info, languages, commits, contributors, readme, contents = await asyncio.gather(
            repo_task,
            languages_task,
            commits_task,
            contributors_task,
            readme_task,
            contents_task,
        )

    if repository_info is None:
        raise HTTPException(status_code=404, detail="Public GitHub repository not found.")

    if not isinstance(languages, dict):
        languages = {}
    if not isinstance(commits, list):
        commits = []
    if not isinstance(contributors, list):
        contributors = []
    if not isinstance(contents, list):
        contents = []

    checks = build_health_checks(repository_info, contents, readme)
    score = round(sum(1 for check in checks if check["passed"]) / len(checks) * 100)

    language_total = sum(languages.values()) or 1
    language_breakdown = [
        {
            "name": name,
            "bytes": byte_count,
            "percentage": round(byte_count / language_total * 100, 1),
        }
        for name, byte_count in sorted(languages.items(), key=lambda item: item[1], reverse=True)
    ]

    recent_commits = []
    for item in commits[:5]:
        commit = item.get("commit", {})
        author = commit.get("author") or {}
        recent_commits.append({
            "sha": item.get("sha", "")[:7],
            "message": (commit.get("message") or "No commit message").splitlines()[0],
            "author": author.get("name") or item.get("author", {}).get("login") or "Unknown",
            "date": author.get("date"),
            "url": item.get("html_url"),
        })

    top_contributors = [
        {
            "login": item.get("login", "unknown"),
            "avatar_url": item.get("avatar_url"),
            "contributions": item.get("contributions", 0),
            "url": item.get("html_url"),
        }
        for item in contributors[:5]
    ]

    license_info = repository_info.get("license") or {}
    report = {
        "repository": {
            "owner": repository_info.get("owner", {}).get("login", owner),
            "name": repository_info.get("name", repo),
            "full_name": repository_info.get("full_name", f"{owner}/{repo}"),
            "html_url": repository_info.get("html_url", f"https://github.com/{owner}/{repo}"),
            "description": repository_info.get("description"),
            "stars": repository_info.get("stargazers_count", 0),
            "forks": repository_info.get("forks_count", 0),
            "open_issues": repository_info.get("open_issues_count", 0),
            "primary_language": repository_info.get("language"),
            "license": license_info.get("spdx_id") or license_info.get("name"),
            "default_branch": repository_info.get("default_branch"),
            "created_at": repository_info.get("created_at"),
            "updated_at": repository_info.get("updated_at"),
        },
        "health_score": score,
        "health_checks": checks,
        "languages": language_breakdown,
        "recent_commits": recent_commits,
        "contributors": top_contributors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "score_note": "Repository hygiene indicator only; not a security audit or developer skill measure.",
    }

    result = await db.execute(
        select(Repository).where(
            Repository.owner == report["repository"]["owner"],
            Repository.name == report["repository"]["name"],
        )
    )
    stored_repo = result.scalar_one_or_none()
    license_name = report["repository"]["license"]

    if stored_repo is None:
        stored_repo = Repository(
            owner=report["repository"]["owner"],
            name=report["repository"]["name"],
            github_url=report["repository"]["html_url"],
            description=report["repository"]["description"],
            stars=report["repository"]["stars"],
            forks=report["repository"]["forks"],
            open_issues=report["repository"]["open_issues"],
            primary_language=report["repository"]["primary_language"],
            license_name=license_name,
        )
        db.add(stored_repo)
    else:
        stored_repo.github_url = report["repository"]["html_url"]
        stored_repo.description = report["repository"]["description"]
        stored_repo.stars = report["repository"]["stars"]
        stored_repo.forks = report["repository"]["forks"]
        stored_repo.open_issues = report["repository"]["open_issues"]
        stored_repo.primary_language = report["repository"]["primary_language"]
        stored_repo.license_name = license_name

    await db.flush()
    db.add(
        AnalysisReport(
            repository_id=stored_repo.id,
            health_score=score,
            report_data=report,
        )
    )
    await db.commit()
    return report


@app.get("/api/history")
async def list_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    result = await db.execute(
        select(AnalysisReport, Repository)
        .join(Repository, AnalysisReport.repository_id == Repository.id)
        .order_by(desc(AnalysisReport.created_at))
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": report.id,
            "repository": f"{repository.owner}/{repository.name}",
            "github_url": repository.github_url,
            "health_score": report.health_score,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
        for report, repository in rows
    ]


@app.get("/api/history/{report_id}")
async def get_history_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Saved analysis report not found.")
    return {
        "id": report.id,
        "health_score": report.health_score,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "report": report.report_data,
    }
