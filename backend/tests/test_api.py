
import pytest
from fastapi.testclient import TestClient

import main


class FakeResult:
    def scalar_one_or_none(self):
        return None

    def all(self):
        return []


class FakeDatabase:
    def __init__(self):
        self.added = []

    async def execute(self, statement):
        return FakeResult()

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        # Simulate the database assigning an ID to a new repository.
        for item in self.added:
            if isinstance(item, main.Repository) and item.id is None:
                item.id = 1

    async def commit(self):
        pass


@pytest.fixture
def api_client():
    database = FakeDatabase()

    async def override_get_db():
        yield database

    main.app.dependency_overrides[main.get_db] = override_get_db

    # Do not use a TestClient context manager here: that would start
    # the real application lifespan and connect to the configured database.
    with_client = TestClient(main.app)
    yield with_client

    main.app.dependency_overrides.clear()


def test_invalid_repository_name_returns_400(api_client):
    response = api_client.get("/api/analyze/../repo")

    # Some HTTP clients normalize paths containing ../ before sending them.
    # Use an invalid owner that does not need path normalization instead.
    if response.status_code != 400:
        response = api_client.get("/api/analyze/bad%21owner/repo")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid GitHub owner or repository name."
    )


def test_missing_repository_returns_404(api_client, monkeypatch):
    async def fake_github_get(client, path):
        if path == "/repos/test-owner/missing-repo":
            return None
        if path.endswith("/languages"):
            return {}
        if "/commits?" in path or "/contributors?" in path:
            return []
        if path.endswith("/readme"):
            return None
        if path.endswith("/contents"):
            return []
        return {}

    monkeypatch.setattr(main, "github_get", fake_github_get)

    response = api_client.get(
        "/api/analyze/test-owner/missing-repo"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Public GitHub repository not found."
    )


def test_github_rate_limit_returns_429(api_client, monkeypatch):
    from fastapi import HTTPException

    async def fake_github_get(client, path):
        raise HTTPException(
            status_code=429,
            detail=(
                "GitHub API rate limit reached. "
                "Add a server-side GITHUB_TOKEN and try again later."
            ),
        )

    monkeypatch.setattr(main, "github_get", fake_github_get)

    response = api_client.get(
        "/api/analyze/test-owner/test-repo"
    )

    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_history_returns_empty_list(api_client):
    response = api_client.get("/api/history")

    assert response.status_code == 200
    assert response.json() == []


def test_missing_history_report_returns_404(api_client):
    response = api_client.get("/api/history/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Saved analysis report not found."
    )

def test_successful_repository_analysis(api_client, monkeypatch):
    async def fake_github_get(client, path):
        if path == "/repos/test-owner/test-repo":
            return {
                "owner": {"login": "test-owner"},
                "name": "test-repo",
                "full_name": "test-owner/test-repo",
                "html_url": "https://github.com/test-owner/test-repo",
                "description": "A test repository",
                "stargazers_count": 5,
                "forks_count": 1,
                "open_issues_count": 0,
                "language": "Python",
                "license": {"spdx_id": "MIT", "name": "MIT License"},
                "default_branch": "main",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
            }

        if path.endswith("/languages"):
            return {"Python": 1000, "HTML": 250}

        if "/commits?" in path:
            return [{
                "sha": "abcdef1234567",
                "commit": {
                    "message": "Add tests",
                    "author": {
                        "name": "Test Author",
                        "date": "2026-01-02T00:00:00Z",
                    },
                },
                "html_url": (
                    "https://github.com/test-owner/test-repo/commit/abcdef"
                ),
            }]

        if "/contributors?" in path:
            return [{
                "login": "test-author",
                "avatar_url": "https://example.com/avatar.png",
                "contributions": 3,
                "html_url": "https://github.com/test-author",
            }]

        if path.endswith("/readme"):
            return {"size": 500}

        if path.endswith("/contents"):
            return [
                {"name": "tests", "type": "dir"},
                {"name": ".github", "type": "dir"},
            ]

        return {}

    monkeypatch.setattr(main, "github_get", fake_github_get)

    response = api_client.get(
        "/api/analyze/test-owner/test-repo"
    )

    assert response.status_code == 200
    report = response.json()

    assert report["repository"]["full_name"] == (
        "test-owner/test-repo"
    )
    assert report["health_score"] == 100
    assert len(report["health_checks"]) == 5
    assert all(check["passed"] for check in report["health_checks"])
    assert report["languages"][0]["name"] == "Python"
    assert report["recent_commits"][0]["message"] == "Add tests"
    assert report["contributors"][0]["login"] == "test-author"
    assert "generated_at" in report

from datetime import datetime, timezone


def test_health_returns_503_when_database_fails(api_client):
    class BrokenDatabase:
        async def execute(self, statement):
            raise RuntimeError("Simulated database failure")

    async def override_broken_db():
        yield BrokenDatabase()

    main.app.dependency_overrides[main.get_db] = override_broken_db

    response = api_client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database connection failed."


def test_history_report_returns_saved_report(api_client):
    saved_report = main.AnalysisReport(
        id=42,
        health_score=85,
        report_data={"repository": {"full_name": "test-owner/test-repo"}},
        created_at=datetime.now(timezone.utc),
    )

    class SavedReportResult:
        def scalar_one_or_none(self):
            return saved_report

    class HistoryDatabase:
        async def execute(self, statement):
            return SavedReportResult()

    async def override_history_db():
        yield HistoryDatabase()

    main.app.dependency_overrides[main.get_db] = override_history_db

    response = api_client.get("/api/history/42")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["health_score"] == 85
    assert data["report"]["repository"]["full_name"] == (
        "test-owner/test-repo"
    )
    assert data["created_at"] is not None

import httpx
import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_github_timeout_returns_502():
    async def handler(request):
        raise httpx.ReadTimeout("Simulated timeout")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(HTTPException) as exc_info:
            await main.github_get(client, "/repos/test-owner/test-repo")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Could not reach the GitHub API."


@pytest.mark.asyncio
async def test_github_forbidden_without_rate_limit_returns_502():
    async def handler(request):
        return httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "10"},
            json={"message": "Forbidden"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(HTTPException) as exc_info:
            await main.github_get(client, "/repos/test-owner/test-repo")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "GitHub denied the API request."


@pytest.mark.asyncio
async def test_github_server_error_returns_502():
    async def handler(request):
        return httpx.Response(500, json={"message": "Server error"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(HTTPException) as exc_info:
            await main.github_get(client, "/repos/test-owner/test-repo")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "GitHub API returned 500."

def test_analysis_updates_existing_repository(api_client, monkeypatch):
    from types import SimpleNamespace

    existing_repository = SimpleNamespace(
        id=7,
        owner="test-owner",
        name="test-repo",
        github_url="https://github.com/test-owner/test-repo",
        description="Old description",
        stars=1,
        forks=0,
        open_issues=0,
        primary_language="JavaScript",
        license_name=None,
    )

    class ExistingRepositoryResult:
        def scalar_one_or_none(self):
            return existing_repository

    class ExistingRepositoryDatabase:
        def __init__(self):
            self.added = []
            self.commit_called = False

        async def execute(self, statement):
            return ExistingRepositoryResult()

        def add(self, item):
            self.added.append(item)

        async def flush(self):
            pass

        async def commit(self):
            self.commit_called = True

    database = ExistingRepositoryDatabase()

    async def override_get_db():
        yield database

    main.app.dependency_overrides[main.get_db] = override_get_db

    async def fake_github_get(client, path):
        if path == "/repos/test-owner/test-repo":
            return {
                "owner": {"login": "test-owner"},
                "name": "test-repo",
                "full_name": "test-owner/test-repo",
                "html_url": "https://github.com/test-owner/test-repo",
                "description": "Updated description",
                "stargazers_count": 10,
                "forks_count": 2,
                "open_issues_count": 3,
                "language": "Python",
                "license": {"spdx_id": "MIT", "name": "MIT License"},
                "default_branch": "main",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
            }
        if path.endswith("/languages"):
            return {"Python": 100}
        if "/commits?" in path or "/contributors?" in path:
            return []
        if path.endswith("/readme"):
            return {"size": 100}
        if path.endswith("/contents"):
            return [
                {"name": "tests"},
                {"name": ".github"},
            ]
        return {}

    monkeypatch.setattr(main, "github_get", fake_github_get)

    response = api_client.get("/api/analyze/test-owner/test-repo")

    assert response.status_code == 200
    assert existing_repository.description == "Updated description"
    assert existing_repository.stars == 10
    assert existing_repository.forks == 2
    assert existing_repository.open_issues == 3
    assert existing_repository.primary_language == "Python"
    assert existing_repository.license_name == "MIT"
    assert database.commit_called
    assert len(database.added) == 1
    assert isinstance(database.added[0], main.AnalysisReport)

def test_analysis_creates_new_repository(api_client, monkeypatch):
    class NewRepositoryDatabase:
        def __init__(self):
            self.added = []
            self.flush_called = False
            self.commit_called = False

        async def execute(self, statement):
            # No repository exists yet.
            return FakeResult()

        def add(self, item):
            self.added.append(item)

        async def flush(self):
            self.flush_called = True
            for item in self.added:
                if isinstance(item, main.Repository) and item.id is None:
                    item.id = 99

        async def commit(self):
            self.commit_called = True

    database = NewRepositoryDatabase()

    async def override_get_db():
        yield database

    main.app.dependency_overrides[main.get_db] = override_get_db

    async def fake_github_get(client, path):
        if path == "/repos/test-owner/new-repo":
            return {
                "owner": {"login": "test-owner"},
                "name": "new-repo",
                "full_name": "test-owner/new-repo",
                "html_url": "https://github.com/test-owner/new-repo",
                "description": "A newly analyzed repository",
                "stargazers_count": 2,
                "forks_count": 0,
                "open_issues_count": 0,
                "language": "Python",
                "license": {"spdx_id": "MIT", "name": "MIT License"},
                "default_branch": "main",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
            }
        if path.endswith("/languages"):
            return {"Python": 100}
        if "/commits?" in path or "/contributors?" in path:
            return []
        if path.endswith("/readme"):
            return {"size": 100}
        if path.endswith("/contents"):
            return [{"name": "tests"}, {"name": ".github"}]
        return {}

    monkeypatch.setattr(main, "github_get", fake_github_get)

    response = api_client.get("/api/analyze/test-owner/new-repo")

    assert response.status_code == 200
    assert response.json()["repository"]["full_name"] == (
        "test-owner/new-repo"
    )
    assert database.flush_called
    assert database.commit_called

    repository_records = [
        item for item in database.added
        if isinstance(item, main.Repository)
    ]
    report_records = [
        item for item in database.added
        if isinstance(item, main.AnalysisReport)
    ]

    assert len(repository_records) == 1
    assert repository_records[0].id == 99
    assert len(report_records) == 1
    assert report_records[0].repository_id == 99

@pytest.mark.asyncio
async def test_github_headers_without_token(monkeypatch):
    monkeypatch.setattr(main, "GITHUB_TOKEN", "")

    headers = main.github_headers()

    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert headers["User-Agent"] == "RepoLens"
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_github_headers_with_token(monkeypatch):
    monkeypatch.setattr(main, "GITHUB_TOKEN", "test-token")

    headers = main.github_headers()

    assert headers["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_github_not_found_returns_none():
    async def handler(request):
        return httpx.Response(404, json={"message": "Not Found"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await main.github_get(
            client, "/repos/test-owner/missing-repo"
        )

    assert result is None


@pytest.mark.asyncio
async def test_github_rate_limit_response_returns_429():
    async def handler(request):
        return httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "0"},
            json={"message": "API rate limit exceeded"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(HTTPException) as exc_info:
            await main.github_get(
                client, "/repos/test-owner/test-repo"
            )

    assert exc_info.value.status_code == 429


def test_build_health_checks_with_missing_project_files():
    repo = {
        "description": "",
        "license": None,
    }

    checks = main.build_health_checks(
        repo=repo,
        root_items=[{"name": "src", "type": "dir"}],
        readme=None,
    )

    assert len(checks) == 5
    assert all(check["passed"] is False for check in checks)


def test_build_health_checks_handles_unexpected_root_items():
    repo = {
        "description": "A sample project",
        "license": {"spdx_id": "NOASSERTION"},
    }

    checks = main.build_health_checks(
        repo=repo,
        root_items=[None, "unexpected", {"name": "src"}],
        readme={"size": 100},
    )

    results = {check["key"]: check["passed"] for check in checks}

    assert results["description"] is True
    assert results["readme"] is True
    assert results["license"] is False
    assert results["tests"] is False
    assert results["workflows"] is False


def test_history_returns_saved_rows(api_client):
    from datetime import datetime, timezone
    from types import SimpleNamespace

    saved_repository = SimpleNamespace(
        id=7,
        owner="test-owner",
        name="test-repo",
        github_url="https://github.com/test-owner/test-repo",
    )
    saved_report = SimpleNamespace(
        id=42,
        repository_id=7,
        health_score=85,
        created_at=datetime.now(timezone.utc),
    )

    class PopulatedHistoryResult:
        def all(self):
            return [(saved_report, saved_repository)]

    class PopulatedHistoryDatabase:
        async def execute(self, statement):
            return PopulatedHistoryResult()

    async def override_get_db():
        yield PopulatedHistoryDatabase()

    main.app.dependency_overrides[main.get_db] = override_get_db

    response = api_client.get("/api/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 42
    assert data[0]["repository"] == "test-owner/test-repo"
    assert data[0]["health_score"] == 85
    assert data[0]["github_url"] == (
        "https://github.com/test-owner/test-repo"
    )
    assert data[0]["created_at"] is not None

