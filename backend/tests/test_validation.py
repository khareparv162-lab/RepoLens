import re

OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def valid_repo_name(owner: str, repo: str) -> bool:
    return bool(OWNER_PATTERN.fullmatch(owner)) and bool(REPO_PATTERN.fullmatch(repo)) and repo not in {".", ".."}


def test_valid_owner_and_repo():
    assert valid_repo_name("octocat", "Hello-World")
    assert valid_repo_name("my-org", "repo.js")


def test_rejects_invalid_names():
    assert not valid_repo_name("../bad", "repo")
    assert not valid_repo_name("owner", "..")
    assert not valid_repo_name("owner", "bad/repo")
