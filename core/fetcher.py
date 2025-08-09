# core/fetcher.py
import logging
from typing import List, Dict, Any
from services.github_service import GitHubService

logger = logging.getLogger(__name__)

class RepoFetcher:
    def __init__(self, github_service: GitHubService):
        self.github_service = github_service

    def fetch_files(self, owner: str, repo: str) -> tuple[List[Dict[str, Any]], str | None]:
        return self.github_service.get_repo_contents(owner, repo)