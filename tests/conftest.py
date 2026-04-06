import os

def pytest_configure(config):
    os.environ.setdefault("GIT_REPO_URL", "https://example.com/repo.git")
