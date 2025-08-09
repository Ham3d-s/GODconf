# services/github_service.py
import logging
from typing import Dict, Any, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import settings

logger = logging.getLogger(__name__)

class GitHubService:
    """
    این کلاس تمام تعاملات با GitHub API را مدیریت می‌کند.
    این کلاس یک Session پایدار با قابلیت تلاش مجدد خودکار ایجاد می‌کند.
    """
    def __init__(self):
        self.session = self._create_resilient_session()

    def _create_resilient_session(self) -> requests.Session:
        session = requests.Session()
        headers = {'Accept': 'application/vnd.github.v3+json'}

        # FIX: از متد جدید و امن get_api_key برای خواندن توکن استفاده می‌شود
        github_token = settings.get_api_key("GITHUB_TOKEN")

        if github_token:
            logger.info("Using GITHUB_TOKEN for authentication.")
            headers['Authorization'] = f"token {github_token}"
        else:
            logger.warning("No GITHUB_TOKEN found. Using unauthenticated requests (rate limit is 60/hour).")

        session.headers.update(headers)

        retry_settings = settings.get('retry_settings', {})
        retry_strategy = Retry(
            total=retry_settings.get('total', 3),
            backoff_factor=retry_settings.get('backoff_factor', 1),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        pool_size = settings.get('max_workers', 10)
        adapter = HTTPAdapter(pool_maxsize=pool_size, max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        logger.info(f"Resilient session created with pool size of {pool_size}.")
        return session

    def get_repo_contents(self, owner: str, repo: str) -> Tuple[List[Dict[str, Any]], str | None]:
        logger.info(f"Fetching file tree for repository: {owner}/{repo}")
        api_base_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            repo_info_res = self.session.get(api_base_url, timeout=settings.get('request_timeout', 15))
            repo_info_res.raise_for_status()
            repo_json = repo_info_res.json()
            default_branch = repo_json.get("default_branch", "main")

            tree_url = f"{api_base_url}/git/trees/{default_branch}?recursive=1"
            tree_res = self.session.get(tree_url, timeout=settings.get('request_timeout', 30))
            tree_res.raise_for_status()
            return tree_res.json().get('tree', []), default_branch
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching repo info for {owner}/{repo}: {e}")
            return [], None

    def download_file_content(self, download_url: str) -> str | None:
        try:
            response = self.session.get(download_url, timeout=settings.get('request_timeout', 10))
            if response.status_code == 200:
                return response.text
            logger.warning(f"Failed to download {download_url}. Status: {response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {download_url}: {e}")
            return None